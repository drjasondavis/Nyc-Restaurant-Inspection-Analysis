import unittest
import bizname_comparer

class BiznameComparerTests(unittest.TestCase):
    
    def test_canonicalize(self):
        c = bizname_comparer.BiznameComparer()
        self.assertEquals('jewel bako', c.canonicalize_name('/biz/jewel-bako', True))
        self.assertEquals('jewel bako', c.canonicalize_name('/biz/jewel-bako-new-york', True))
        self.assertEquals('jewel bako', c.canonicalize_name('/biz/jewel-bako-manhattan', True))
        self.assertEquals('jewel bako', c.canonicalize_name('/biz/jewel-bako-new-york-2', True))
        self.assertEquals('jewel bakos', c.canonicalize_name("/biz/jewel-bako's", True))
        self.assertEquals('jewel bako', c.canonicalize_name("JEWEL BAKO", False))
        self.assertEquals('jewel bako', c.canonicalize_name("JEWEL-BAKO", False))

    def test_compare(self):
        c = bizname_comparer.BiznameComparer()
        self.assertAlmostEquals(1.0, c.compare('jewel bako', '/biz/jewel-bako'))
        self.assertAlmostEquals(1.0, c.compare('jewel and bako', '/biz/jewel-bako'))
        self.assertAlmostEquals(1.0, c.compare('jewel and bako', '/biz/jewel-and-bako'))
        self.assertAlmostEquals(1.0, c.compare('jewel & bako', '/biz/jewel-and-bako'))
        self.assertAlmostEquals(0.5, c.compare('jewel', '/biz/jewel-bako'))
        self.assertAlmostEquals(1.0, c.compare('DIWAN-E-KHAAS', '/biz/diwan-e-khaas-new-york-3'))
        self.assertAlmostEquals(1.0, c.compare("DONOHUE'S STEAK HOUSE", "/biz/donohues-steak-house-new-york"))
        self.assertAlmostEquals(0.0, c.compare('DIANA CENTER CAFETERIA', '/biz/francesco-new-york'))

if __name__ == '__main__':
    unittest.main()

