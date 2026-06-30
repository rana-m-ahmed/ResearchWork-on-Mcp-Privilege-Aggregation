import os
import json
import uuid
import shutil
from phase3.core.task_loader import TaskLoader
from phase3.core.logger import TrialLogger
from phase3.core.orchestrator import Phase3Orchestrator

def setup_test_files():
    os.makedirs('test_data', exist_ok=True)
    os.makedirs('phase3/logs', exist_ok=True)
    
    with open('test_data/test_matrix.csv', 'w') as f:
        f.write("model,density,surface,task_id,is_warmup\n")
        for i in range(10):
            f.write(f"M3,1,CLEAN,task_{i},false\n")
            
    with open('test_data/test_tasks.jsonl', 'w') as f:
        for i in range(15):
            f.write(json.dumps({'task_id': f'task_{i}', 'user_task': 'do something'}) + '\n')
            
    if os.path.exists('phase3/logs/trials_M3_test.jsonl'):
        os.remove('phase3/logs/trials_M3_test.jsonl')

def test_task_loader():
    loader = TaskLoader()
    trials = loader.load_trials('test_data/test_matrix.csv', 'test_data/test_tasks.jsonl')
    assert len(trials) == 10, f"Expected 10 trials, got {len(trials)}"
    assert trials[0].task_id == 'task_0'
    print("PASS: TaskLoader loaded trials correctly.")

def test_logger():
    log_path = 'phase3/logs/trials_M3_test.jsonl'
    logger = TrialLogger(log_path)
    
    logger.append_result({'trial_id': 'task_0', 'trial_acceptance_valid': True, 'counts_toward_cell_n': True})
    logger.append_result({'trial_id': 'task_1', 'trial_acceptance_valid': True, 'counts_toward_cell_n': True})
    
    # Try duplicate
    logger.append_result({'trial_id': 'task_0', 'trial_acceptance_valid': True, 'counts_toward_cell_n': True})
    logger.close()
    
    # Check on disk
    with open(log_path, 'r') as f:
        lines = f.readlines()
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"
    print("PASS: Logger dedupes and flushes properly.")
    
    # Test resume
    logger2 = TrialLogger(log_path)
    assert logger2.count_valid_trials() == 2
    assert len(logger2.get_completed_trial_ids()) == 2
    logger2.close()
    print("PASS: Logger resumes correctly.")

def test_orchestrator():
    config = {'model_name': 'mock'}
    orchestrator = Phase3Orchestrator(config, 'M3_test')
    
    orchestrator.required_trials = 5
    
    class MockBackend:
        def load_model(self, model): pass
        def unload_model(self): pass
        def generate(self, prompt, params): return {"raw_output": "mock", "backend_parameters": {}}
        def health_check(self): return True
        def metadata(self): return {}
        
    orchestrator.backend = MockBackend()
    
    status = orchestrator.execute_batch('test_data/test_matrix.csv', 'test_data/test_tasks.jsonl')
    assert status.valid_trials_completed == 5, f"Expected 5, got {status.valid_trials_completed}"
    
    logger3 = TrialLogger('phase3/logs/trials_M3_test.jsonl')
    assert logger3.count_valid_trials() == 5
    logger3.close()
    
    status2 = orchestrator.execute_batch('test_data/test_matrix.csv', 'test_data/test_tasks.jsonl')
    assert status2.total_trials_run == 0
    assert status2.valid_trials_completed == 5
    print("PASS: Orchestrator executed, logged, and skipped completed trials.")

if __name__ == '__main__':
    try:
        setup_test_files()
        test_task_loader()
        test_logger()
        test_orchestrator()
    finally:
        if os.path.exists('test_data'):
            shutil.rmtree('test_data')
