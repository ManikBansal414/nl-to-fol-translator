import json
import sys
import os
from io import StringIO

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import RobustSystem
import resolution_engine.Resolution as Res

def run_tests(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    tests = data['tests']
    passed = 0
    failed = 0
    results_summary = []

    print(f"Running {len(tests)} tests from {json_file}...\n")

    for test in tests:
        test_name = test['name']
        steps = test['steps']
        expected_results = test['expected']
        
        # Reset System for each test
        Res.KNOWLEDGE_BASE = set()
        Res.KNOWLEDGE_BASE_HASH = {}
        Res.STANDARD_VARIABLE_COUNT = 0
        system = RobustSystem()
        
        # Capture stdout to keep output clean
        held_stdout = sys.stdout
        sys.stdout = StringIO()
        
        current_expected_idx = 0
        test_failed = False
        failure_reason = ""

        try:
            for step in steps:
                action = step[0]
                sentence = step[1]
                
                if action == "add":
                    system.add_fact(sentence)
                elif action == "query":
                    result = system.query(sentence)
                    expected = expected_results[current_expected_idx]
                    current_expected_idx += 1
                    
                    if result != expected:
                        test_failed = True
                        failure_reason = f"Query '{sentence}' returned {result}, expected {expected}"
                        break
        except Exception as e:
            test_failed = True
            failure_reason = f"Exception: {str(e)}"
        finally:
            sys.stdout = held_stdout

        if test_failed:
            failed += 1
            print(f"❌ FAIL: {test_name}")
            print(f"   Reason: {failure_reason}")
        else:
            passed += 1
            print(f"✅ PASS: {test_name}")

    print(f"\nTotal Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 run_json_tests.py <test_file.json>")
        sys.exit(1)
    
    run_tests(sys.argv[1])
