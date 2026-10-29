"""Scientific invariants for paired three-method uncertainty propagation."""
import unittest
import numpy as np
from summarize import aggregate

class PairedComparisonTests(unittest.TestCase):
    def test_identical_methods_remain_identical_after_resampling(self):
        rng=np.random.default_rng(22)
        ratio=np.exp(rng.normal(0,.05,(10,2000)))
        draws=np.stack([ratio,ratio,np.ones_like(ratio)],axis=-1)
        nominal=np.stack([ratio.mean(1),ratio.mean(1),np.ones(10)],axis=-1)
        point,boot=aggregate(draws,nominal,44,2000)
        np.testing.assert_allclose(boot[:,0],boot[:,1])
        np.testing.assert_allclose(boot[:,2],1)
        self.assertEqual(point[2],1)

    def test_ratios_preserve_transitivity_in_every_paired_draw(self):
        rng=np.random.default_rng(23)
        a,b=np.exp(rng.normal(0,.05,(2,10,2000)))
        draws=np.stack([a,b,a/b],axis=-1)
        nominal=np.exp(np.mean(np.log(draws),axis=1))
        point,boot=aggregate(draws,nominal,45,2000)
        np.testing.assert_allclose(boot[:,0]/boot[:,1],boot[:,2],rtol=1e-12)
        self.assertAlmostEqual(point[0]/point[1],point[2])

if __name__=='__main__':unittest.main()
