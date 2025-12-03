import sys
import os
import re
from typing import List

# Add current directory and resolution_engine to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'resolution_engine'))

from translator import translate_sentence
from resolution_engine.Resolution import run_resolution_engine

class FOLConverter:
    def __init__(self):
        self.skolem_count = 0

    def convert(self, fol: str, is_query: bool = False) -> str:
        # 1. Normalize operators
        # My translator: forall x. (Human(x) -> Mortal(x))
        # Target: (Human(x) => Mortal(x))
        
        converted = fol
        
        # Replace -> with =>
        converted = converted.replace('->', '=>')
        
        # Replace <-> with equivalent (A => B) & (B => A)
        # This is hard to do with simple replace without parsing. 
        # For now, assume the translator prefers -> and &
        
        # Replace 'not ' with '~'
        converted = converted.replace('not ', '~')
        
        # Handle Quantifiers
        # Strategy: 
        # - Remove 'forall [var].'
        # - Remove 'exists [var].' and replace [var] with Skolem Constant
        
        # Find all quantifiers
        while True:
            match = re.search(r'(forall|exists)\s+([a-z0-9]+)\.\s*', converted)
            if not match:
                break
            
            q_type, var = match.groups()
            full_match = match.group(0)
            
            if q_type == 'forall':
                if is_query:
                    # For QUERY 'forall x. P(x)', we want to prove it by contradiction.
                    # Negation is 'exists x. ~P(x)'.
                    # This requires a Skolem constant in the negated form.
                    # Since the engine negates the input string, we must provide a string 
                    # that, when negated, produces Skolem constants.
                    # Actually, the engine treats variables as universal.
                    # If we pass 'P(x)', engine negates to '~P(x)' (Universal).
                    # This tests 'exists x. P(x)'.
                    
                    # If we want to test 'forall x. P(x)', we need the negation to be '~P(Skolem)'.
                    # So we should pass 'P(Skolem)'.
                    
                    skolem_const = f"Skolem{var.upper()}{self.skolem_count}"
                    self.skolem_count += 1
                    converted = converted.replace(full_match, '', 1)
                    converted = re.sub(r'\b' + var + r'\b', skolem_const, converted)
                else:
                    # For FACT, 'forall' is just a variable
                    converted = converted.replace(full_match, '', 1)
                    
            elif q_type == 'exists':
                if is_query:
                    # For QUERY 'exists x. P(x)', we want to prove it by contradiction.
                    # Negation is 'forall x. ~P(x)'.
                    # This requires a Variable in the negated form.
                    # So we should pass 'P(x)'.
                    converted = converted.replace(full_match, '', 1)
                else:
                    # For FACT, 'exists' implies a specific instance (Skolem)
                    skolem_const = f"Skolem{var.upper()}{self.skolem_count}"
                    self.skolem_count += 1
                    converted = converted.replace(full_match, '', 1)
                    converted = re.sub(r'\b' + var + r'\b', skolem_const, converted)

        # Clean up extra parentheses if any (translator produces outer parens sometimes)
        converted = converted.strip()
        
        # The resolution engine expects predicates like P(x,y).
        # My translator produces P(x, y) (with space).
        converted = converted.replace(', ', ',')
        
        return converted

class RobustSystem:
    def __init__(self):
        self.kb_sentences: List[str] = []
        self.converter = FOLConverter()

    def add_fact(self, nl_sentence: str):
        print(f"Processing Fact: {nl_sentence}")
        fol = translate_sentence(nl_sentence)
        if fol.startswith("[ERROR]"):
            print(f"  Error translating: {fol}")
            return
        
        print(f"  FOL: {fol}")
        converted = self.converter.convert(fol)
        print(f"  Converted for Resolution: {converted}")
        self.kb_sentences.append(converted)

    def query(self, nl_query: str):
        print(f"\nProcessing Query: {nl_query}")
        fol = translate_sentence(nl_query)
        if fol.startswith("[ERROR]"):
            print(f"  Error translating: {fol}")
            return None  # Return None to indicate translation failure

        print(f"  FOL: {fol}")
        # For query, we don't add it to KB. The resolution engine takes queries separately.
        # Note: The resolution engine negates the query internally.
        converted_query = self.converter.convert(fol, is_query=True)
        print(f"  Converted Query: {converted_query}")

        # Prepare input.txt
        self._write_input_file(converted_query)
        
        # Run Resolution
        print("  Running Resolution Engine...")
        try:
            # Capture output to avoid clutter
            # But run_resolution_engine prints a lot.
            # We might want to suppress stdout or just let it print.
            results = run_resolution_engine('input.txt', 'output.txt')
            result = results[0] if results else False
            
            print(f"  Result: {result}")
            if result:
                print("  ✅ TRUE (Entailed)")
            else:
                print("  ❌ FALSE (Not Entailed)")
            
            return result
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  Error running resolution: {e}")
            return False

    def _write_input_file(self, query_str: str):
        with open('input.txt', 'w') as f:
            # Format:
            # <NUMBER OF QUERIES>
            # <QUERY 1>
            # ...
            # <NUMBER OF KB SENTENCES>
            # <SENTENCE 1>
            # ...
            
            f.write("1\n")
            f.write(f"{query_str}\n")
            f.write(f"{len(self.kb_sentences)}\n")
            for sent in self.kb_sentences:
                f.write(f"{sent}\n")

def main():
    system = RobustSystem()
    
    print("=== Robust NL-to-FOL Resolution System ===")
    print("Enter 'add <sentence>' to add to KB.")
    print("Enter 'query <sentence>' to check entailment.")
    print("Enter 'exit' to quit.")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                break
            
            if user_input.lower().startswith('add '):
                sentence = user_input[4:].strip()
                system.add_fact(sentence)
            elif user_input.lower().startswith('query '):
                sentence = user_input[6:].strip()
                system.query(sentence)
            else:
                print("Unknown command. Use 'add' or 'query'.")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
