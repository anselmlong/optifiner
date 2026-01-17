#!/usr/bin/env python3
"""Test script to run baseline evaluation in isolation on apps/workspace/stuckincom1again."""

import json
import logging
import os
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Add worker source to path
project_root = Path(__file__).parent.parent.parent
worker_src = project_root / "services" / "worker" / "src"
sys.path.insert(0, str(worker_src))

try:
    from worker.cli import run_evaluator, run_single_agent_isolated
    logger.info("Successfully imported worker functions")
except ImportError as e:
    logger.error(f"Failed to import worker functions: {e}")
    sys.exit(1)

# Import benchmark builder components
try:
    from worker.benchmark_builder import run_benchmark_builder
    from worker.workspace import WorkspaceManager, set_workspace
    from worker.config import ModelConfig, ModelProvider
    from worker.observability import AgentObserver, set_observer
    from worker.tools.evaluate import set_benchmark_dev_mode
    logger.info("Successfully imported benchmark builder components")
except ImportError as e:
    logger.warning(f"Failed to import benchmark builder components: {e}")
    logger.warning("Benchmark builder will not be available")
    run_benchmark_builder = None

# Import optimization service components
api_src = project_root / "apps" / "api" / "src"
sys.path.insert(0, str(api_src))

from optifiner_api.config import settings
from optifiner_api.services.optimization_service import OptimizationService


def test_baseline_evaluation():
    """Test baseline evaluation on volumetric_particle_sim workspace."""
    
    # Setup workspace path - use volumetric_particle_sim
    workspace_path = project_root / "examples" / "volumetric_particle_sim"
    evaluator_path = str(project_root / "examples" / "volumetric_particle_evaluator.py")
    
    if not workspace_path.exists():
        logger.error(f"Workspace not found: {workspace_path}")
        return False
    
    if not Path(evaluator_path).exists():
        logger.error(f"Evaluator not found: {evaluator_path}")
        return False
    
    logger.info(f"Testing baseline evaluation on workspace: {workspace_path}")
    logger.info(f"Using evaluator: {evaluator_path}")
    
    # Initialize optimization service
    service = OptimizationService()
    
    # Resolve evaluator path to absolute
    evaluator_path_obj = Path(evaluator_path)
    if not evaluator_path_obj.is_absolute():
        evaluator_path_obj = project_root / evaluator_path
    found_evaluator_path = str(evaluator_path_obj.resolve())
    
    # Run baseline evaluation
    logger.info("=" * 60)
    logger.info("RUNNING BASELINE EVALUATION")
    logger.info("=" * 60)
    
    try:
        score, error, data = service._run_evaluator(
            evaluator_path=found_evaluator_path,
            workspace=str(workspace_path),
            timeout=120
        )
        
        logger.info("=" * 60)
        logger.info("BASELINE EVALUATION RESULT")
        logger.info("=" * 60)
        
        if error:
            logger.error(f"Evaluation error: {error}")
            return False
        
        if score is None:
            logger.error("Evaluation returned no score")
            return False
        
        logger.info(f"Baseline Score: {score}")
        
        if data:
            logger.info("Evaluation Data:")
            logger.info(json.dumps(data, indent=2))
        
        logger.info("=" * 60)
        logger.info("BASELINE EVALUATION COMPLETE")
        logger.info("=" * 60)
        
        # Run one iteration of optimization
        logger.info("")
        logger.info("=" * 60)
        logger.info("RUNNING ONE ITERATION OF OPTIMIZATION")
        logger.info("=" * 60)
        
        try:
            # Ensure baseline_data is a dict with proper structure
            if data is None:
                baseline_data_dict = {}
            else:
                baseline_data_dict = dict(data)  # Make a copy
                # Ensure metrics is a dict, not None
                if "metrics" not in baseline_data_dict or baseline_data_dict["metrics"] is None:
                    baseline_data_dict["metrics"] = {}
            
            optimization_success = test_one_optimization_iteration(
                service=service,
                workspace_path=workspace_path,
                evaluator_path=found_evaluator_path,
                baseline_score=score,
                baseline_data=baseline_data_dict
            )
            
            if not optimization_success:
                logger.warning("Optimization iteration completed but may not have improved the score")
                # Don't fail the test if optimization doesn't improve - it's just a test
            
            return True
            
        except Exception as e:
            logger.error(f"Exception during optimization iteration: {e}", exc_info=True)
            # Don't fail the test if optimization fails - baseline was successful
            return True
        
    except Exception as e:
        logger.error(f"Exception during baseline evaluation: {e}", exc_info=True)
        return False


def test_one_optimization_iteration(
    service: OptimizationService,
    workspace_path: Path,
    evaluator_path: str,
    baseline_score: float,
    baseline_data: dict | None
) -> bool:
    """Run one iteration of optimization and evaluate the result.
    
    Args:
        service: OptimizationService instance
        workspace_path: Path to the workspace
        evaluator_path: Path to the evaluator script
        baseline_score: Baseline score to beat
        baseline_data: Baseline evaluation data
        
    Returns:
        True if optimization improved the score, False otherwise
    """
    import asyncio
    import uuid
    import shutil
    
    # Get API key for the agent
    provider = "google"
    model_name = "gemini-2.0-flash-exp"
    api_key_env = "GOOGLE_API_KEY"
    api_key = os.environ.get(api_key_env)
    
    # Try to load from .env file if not in environment
    if not api_key:
        env_file = project_root / "apps" / "api" / ".env"
        if env_file.exists():
            logger.info(f"Loading {api_key_env} from {env_file}")
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{api_key_env}="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    
    if not api_key:
        logger.warning(f"{api_key_env} not set in environment or .env file. Skipping optimization iteration.")
        logger.warning("Please set GOOGLE_API_KEY in your environment or apps/api/.env file")
        return False
    
    # Note: run_single_agent_isolated will create its own isolated workspace
    # We don't need to create instance_workspace manually, but we'll keep the variable
    # for potential fallback cleanup
    instance_id = f"test-{uuid.uuid4().hex[:8]}"
    instance_workspace = None  # Not used, but kept for cleanup logic
    
    # Patch WORKSPACE_BASE to use .test_workspaces so optimization workspaces are preserved
    import worker.workspace as workspace_module
    workspace_base = project_root / "apps" / "workspace" / ".test_workspaces"
    workspace_base.mkdir(parents=True, exist_ok=True)
    original_base = workspace_module.WORKSPACE_BASE
    workspace_module.WORKSPACE_BASE = workspace_base
    
    try:
        # Set API key temporarily
        original_key = os.environ.get(api_key_env)
        os.environ[api_key_env] = api_key
        
        try:
            # Run a single agent in isolation
            logger.info(f"Running optimization agent: {provider}/{model_name}")
            logger.info(f"Instance ID: {instance_id}")
            logger.info(f"Baseline Score: {baseline_score:.4f}")
            
            if run_single_agent_isolated is None:
                logger.error("run_single_agent_isolated not available")
                return False
            
            # Run the agent
            agent_result, workspace_manager = run_single_agent_isolated(
                source_workspace=str(workspace_path),
                evaluator_path=evaluator_path,
                agent_type="optimizer",
                agent_id=instance_id,
                baseline_score=baseline_score,
                task="Optimize this particle simulation for maximum FPS performance. The score equals the FPS. Note: bottleneck is performance, need to compute based on computer time and framed displayed",
                max_iterations=5,  # Limit iterations for testing
                model_provider=provider,
                model_name=model_name,
                verbosity=1,
                baseline_data=baseline_data,
            )
            
            # Log results
            logger.info("=" * 60)
            logger.info("OPTIMIZATION ITERATION RESULT")
            logger.info("=" * 60)
            logger.info(f"Agent ID: {agent_result.agent_id}")
            logger.info(f"Success: {agent_result.success}")
            logger.info(f"Baseline Score: {agent_result.baseline_score:.4f}")
            logger.info(f"Final Score: {agent_result.final_score:.4f}")
            logger.info(f"Improvement: {agent_result.improvement:.4f}")
            logger.info(f"Duration: {agent_result.duration_seconds:.2f}s")
            
            if agent_result.error:
                logger.warning(f"Agent Error: {agent_result.error}")
            
            if agent_result.files_modified:
                logger.info(f"Files Modified: {len(agent_result.files_modified)}")
                for file in agent_result.files_modified[:5]:  # Show first 5
                    logger.info(f"  - {file}")
                if len(agent_result.files_modified) > 5:
                    logger.info(f"  ... and {len(agent_result.files_modified) - 5} more")
            
            # Evaluate the optimized workspace (use the workspace_manager's workspace where agent actually worked)
            agent_workspace = workspace_manager.workspace_root if workspace_manager else instance_workspace
            logger.info("")
            logger.info(f"Evaluating optimized workspace: {agent_workspace}")
            optimized_score, optimized_error, optimized_data = service._run_evaluator(
                evaluator_path=evaluator_path,
                workspace=str(agent_workspace),
                timeout=120
            )
            
            if optimized_error:
                logger.warning(f"Evaluation error: {optimized_error}")
                return False
            
            if optimized_score is None:
                logger.warning("Optimized evaluation returned no score")
                return False
            
            improvement = optimized_score - baseline_score
            improvement_pct = (improvement / baseline_score * 100) if baseline_score > 0 else 0
            
            logger.info("=" * 60)
            logger.info("OPTIMIZATION EVALUATION RESULT")
            logger.info("=" * 60)
            logger.info(f"Baseline Score: {baseline_score:.4f}")
            logger.info(f"Optimized Score: {optimized_score:.4f}")
            logger.info(f"Improvement: {improvement:+.4f} ({improvement_pct:+.2f}%)")
            
            if optimized_data:
                logger.info("Optimized Evaluation Data:")
                logger.info(json.dumps(optimized_data, indent=2))
            
            logger.info("=" * 60)
            
            optimization_success = optimized_score > baseline_score
            if optimization_success:
                logger.info("✓ Optimization improved the score!")
                if workspace_manager:
                    logger.info(f"Keeping workspace for inspection: {workspace_manager.workspace_root}")
                else:
                    logger.info(f"Keeping workspace for inspection: {instance_workspace}")
            else:
                logger.info("✗ Optimization did not improve the score")
            
            # Only cleanup workspace manager if optimization was NOT successful
            # If successful, keep it so user can inspect the optimized code
            if 'workspace_manager' in locals() and workspace_manager:
                if not optimization_success:
                    logger.debug(f"Cleaning up agent workspace (no improvement): {workspace_manager.workspace_root}")
                    workspace_manager.cleanup()
                else:
                    logger.info(f"Preserving agent workspace: {workspace_manager.workspace_root}")
            
            return optimization_success
            
        finally:
            # Restore original API key
            if 'original_key' in locals():
                if original_key is not None:
                    os.environ[api_key_env] = original_key
                elif api_key_env in os.environ:
                    del os.environ[api_key_env]
            
            # Restore WORKSPACE_BASE
            workspace_module.WORKSPACE_BASE = original_base
                
    except Exception as e:
        logger.error(f"Exception during optimization iteration: {e}", exc_info=True)
        # Restore original API key on error
        if 'original_key' in locals():
            if original_key is not None:
                os.environ[api_key_env] = original_key
            elif api_key_env in os.environ:
                del os.environ[api_key_env]
        # Restore WORKSPACE_BASE on error
        if 'original_base' in locals():
            workspace_module.WORKSPACE_BASE = original_base
        # Cleanup workspace manager on error
        if 'workspace_manager' in locals() and workspace_manager:
            workspace_manager.cleanup()
        return False


if __name__ == "__main__":
    success = test_baseline_evaluation()
    sys.exit(0 if success else 1)
