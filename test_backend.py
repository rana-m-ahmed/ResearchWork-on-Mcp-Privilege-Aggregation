import sys
from phase3.backends.backend_factory import create_backend

def test():
    backend = create_backend(config_dict={'model_name': 'mistral-7b-instruct-v0.3'})
    
    # 1. Health check
    is_healthy = backend.health_check()
    print(f"Health check: {is_healthy}")
    
    if not is_healthy:
        print("Skipping generation test because backend is not reachable.")
        return
        
    try:
        backend.load_model('mistral-7b-instruct-v0.3')
        print(f"Model metadata: {backend.metadata()}")
        
        result = backend.generate("Hello", {"temperature": 0.0, "seed": 42})
        print("Generation result:")
        print(result)
        
    finally:
        backend.unload_model()
        print("Model unloaded.")

if __name__ == '__main__':
    test()
