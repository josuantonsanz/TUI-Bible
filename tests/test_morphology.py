
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opengnt_interface.morphology import expand_morphology

class TestMorphology(unittest.TestCase):
    def test_nouns(self):
        # N-GSM -> Sustantivo, genitivo singular masculino
        self.assertEqual(expand_morphology("N-GSM"), "sust, gen, s, m")
        # N-NPM -> Sustantivo, nominativo plural masculino
        self.assertEqual(expand_morphology("N-NPM"), "sust, nom, p, m")

    def test_articles(self):
        # T-ASF -> Artículo definido, acusativo singular femenino
        self.assertEqual(expand_morphology("T-ASF"), "art, acu, s, f")

    def test_verbs_indicative(self):
        # V-PAI-3S -> Verbo, presente activo indicativo, 3ª pers singular
        self.assertEqual(expand_morphology("V-PAI-3S"), "v, pres, act, ind, 3ª pers, s")
        # V-2AAI-3S -> Verbo, 2aor activo indicativo, 3ª pers singular (2aor is 2A? key is 2A)
        # Dictionary has "2A": "2aor"
        # Input V-2AAI-3S. 2A A I.
        self.assertEqual(expand_morphology("V-2AAI-3S"), "v, 2aor, act, ind, 3ª pers, s")

    def test_verbs_participle(self):
        # V-PAP-NSM -> Verbo, presente activo participio, nominativo singular masculino
        self.assertEqual(expand_morphology("V-PAP-NSM"), "v, pres, act, part, nom, s, m")
        
    def test_verbs_second_tense(self):
        # V-2F...
        pass

    def test_adjectives(self):
        # A-DSF -> Adjetivo, dativo singular femenino
        self.assertEqual(expand_morphology("A-DSF"), "adj, dat, s, f")
        
    def test_conjunction(self):
        self.assertEqual(expand_morphology("CONJ"), "conj")

    def test_preposition(self):
        self.assertEqual(expand_morphology("PREP"), "prep")

if __name__ == '__main__':
    unittest.main()
