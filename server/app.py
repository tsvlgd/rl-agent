from openenv.core.env_server import create_web_interface_app
from server.env_logic import CodeReviewEnvironment
from models import CodeReviewAction, CodeReviewObservation

app = create_web_interface_app(
    CodeReviewEnvironment, 
    CodeReviewAction, 
    CodeReviewObservation
)

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()