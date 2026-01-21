# Unit tests for algorithm

import unittest
from src.algorithm import ProfessionalBettingAlgorithm

class TestAlgorithm(unittest.TestCase):
    def setUp(self):
        self.algo = ProfessionalBettingAlgorithm('football')
    
    def test_initialization(self):
        self.assertEqual(self.algo.sport, 'football')
    
    # Add more tests

if __name__ == '__main__':
    unittest.main()
