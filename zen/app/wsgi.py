import sys
sys.path.append("/home/dark/zen")
print(sys.path)
from app import app

if __name__ == "__main__":
	app.run()

