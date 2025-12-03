import sys
import os
import unittest
from io import StringIO

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import RobustSystem

class TestRobustSystem(unittest.TestCase):
    def setUp(self):
        # Reset globals in Resolution engine to avoid state bleeding between tests
        import resolution_engine.Resolution as Res
        Res.KNOWLEDGE_BASE = set()
        Res.KNOWLEDGE_BASE_HASH = {}
        Res.STANDARD_VARIABLE_COUNT = 0
        
        self.system = RobustSystem()
        # Suppress stdout during tests to keep output clean
        self.held_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        sys.stdout = self.held_stdout

    def test_socrates_syllogism(self):
        """Test the classic Socrates syllogism."""
        self.system.add_fact("All humans are mortal")
        self.system.add_fact("Socrates is a human")
        
        # Should be True
        self.assertTrue(self.system.query("Socrates is mortal"), "Socrates should be mortal")

    def test_transitive_chain(self):
        """Test transitive property (A->B, B->C => A->C)."""
        self.system.add_fact("All dogs are mammals")
        self.system.add_fact("All mammals are animals")
        
        self.assertTrue(self.system.query("All dogs are animals"), "All dogs should be animals")

    def test_negative_statement(self):
        """Test handling of negative statements."""
        # "No humans are immortal" -> forall x. Human(x) -> not Immortal(x)
        self.system.add_fact("No humans are immortal")
        self.system.add_fact("Socrates is a human")
        
        # Socrates is immortal? -> False
        self.assertTrue(self.system.query("Socrates is not immortal"), "Socrates should not be immortal")
        
        # Socrates is not immortal? -> True
        # Note: The system needs to handle "Socrates is not immortal" query correctly.
        # If the translator handles "Socrates is not immortal" -> ~Immortal(Socrates)
        # Then query checks if KB |= ~Immortal(Socrates).
        # Resolution negates query: ~~Immortal(Socrates) -> Immortal(Socrates).
        # KB has Human(S) and Human(x)->~Immortal(x) => ~Immortal(S).
        # Resolution: ~Immortal(S) vs Immortal(S) -> Contradiction -> True.
        # self.assertTrue(self.system.query("Socrates is not immortal")) 
        # (Commented out until I verify translator supports this query form)

    def test_existential_import(self):
        """
        Test 'All humans are mortal' -> 'Some humans are mortal'.
        In FOL, this is FALSE unless there is at least one human.
        """
        self.system.add_fact("All humans are mortal")
        
        # Without instances, this should be False
        self.assertFalse(self.system.query("Some humans are mortal"), 
                         "All->Some should fail without instances in strict FOL")
        
        # Add an instance
        self.system.add_fact("Socrates is a human")
        
        # Now it should be True
        self.assertTrue(self.system.query("Some humans are mortal"), 
                        "All->Some should succeed when an instance exists")

    def test_some_implies_not_some_negation(self):
        """
        Test 'Some humans are mortal' -> 'Some humans are not mortal'.
        This should be FALSE.
        """
        self.system.add_fact("Some humans are mortal")
        
        self.assertFalse(self.system.query("Some humans are not mortal"),
                         "'Some are' does not imply 'Some are not'")

    def test_disjoint_sets(self):
        """Test 'No X are Y'."""
        self.system.add_fact("No cats are dogs")
        self.system.add_fact("Garfield is a cat")
        
        self.assertFalse(self.system.query("Garfield is a dog"), "Garfield cannot be a dog")

    def test_entailment(self):
        self.system.add_fact("All humans are mortal")

        self.assertTrue(self.system.query("Some humans are mortal"), "yes")
if __name__ == '__main__':
    # Run tests and print results to stderr (so we see them even if stdout is captured)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRobustSystem)
    unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
