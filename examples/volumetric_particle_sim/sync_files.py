import os
import shutil

src = "particle_sim.py"
dst = "volumetric_particle_sim/particle_sim.py"

if os.path.exists(src) and os.path.exists(dst):
    shutil.copy2(src, dst)
    print(f"Copied {src} to {dst}")
else:
    print("Files not found")
