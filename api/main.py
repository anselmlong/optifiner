import sys
import os

# Add the API source directory to the Python path
# This allows 'from optifiner_api...' imports to work
api_src_path = os.path.join(os.path.dirname(__file__), "..", "apps", "api", "src")
sys.path.append(api_src_path)

from optifiner_api.main import app
