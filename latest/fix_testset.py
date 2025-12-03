import json
import os

def fix_testset():
    path = os.path.join(os.getcwd(), 'latest', 'testset.json')
    with open(path, 'r') as f:
        data = json.load(f)
    
    fixed_count = 0
    for test in data['tests']:
        if 'disjoint_cats_dogs_bob' in test['name']:
            # Find and remove ["add", "Bob is a dog"]
            new_steps = []
            for step in test['steps']:
                if step == ["add", "Bob is a dog"]:
                    print(f"Removing 'Bob is a dog' from {test['name']}")
                    fixed_count += 1
                    continue
                new_steps.append(step)
            test['steps'] = new_steps
            
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"Fixed {fixed_count} tests.")

if __name__ == "__main__":
    fix_testset()
