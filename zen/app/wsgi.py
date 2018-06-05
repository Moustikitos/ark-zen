import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
print(sys.path)
from app import app

if __name__ == "__main__":
	app.run()

