// Regional subgroup analysis, transcribed from subgroup_comparison_parsed.tex.
// Partial Spearman rho, residualised on % under 65 and state fixed effects.
// dRho = subsample rho minus full-sample rho. The parsed table retains only
// rows where dRho < -0.05 (i.e. the access measure performs MEANINGFULLY
// BETTER in the regional subsample). RUCC Code shown in each block as a
// reference. *** p<0.001, ** p<0.01, * p<0.05.

export const regional = [
  {
    region: 'Appalachia',
    outcome: 'Respiratory mortality',
    rows: [
      { predictor: 'RUCC Code', isRef: true, full: '-0.37***', sub: '-0.38***', dRho: -0.01, nFull: '2,186', nSub: '315' },
      { predictor: 'Primary access score', isRef: false, full: '-0.09***', sub: '-0.22***', dRho: -0.12, nFull: '2,186', nSub: '315' },
      { predictor: 'Emergency access score', isRef: false, full: '-0.17***', sub: '-0.38***', dRho: -0.21, nFull: '2,186', nSub: '315' },
    ],
  },
  {
    region: 'Great Plains',
    outcome: 'IHD mortality',
    rows: [
      { predictor: 'RUCC Code', isRef: true, full: '-0.31***', sub: '-0.47***', dRho: -0.16, nFull: '2,642', nSub: '213' },
      { predictor: 'Cardiologists per 10k', isRef: false, full: '-0.17***', sub: '-0.24***', dRho: -0.08, nFull: '2,642', nSub: '213' },
    ],
  },
  {
    region: 'Great Plains',
    outcome: 'Stroke mortality',
    rows: [
      { predictor: 'RUCC Code', isRef: true, full: '-0.21***', sub: '-0.40***', dRho: -0.19, nFull: '1,979', nSub: '99' },
      { predictor: 'EM physicians per 10k', isRef: false, full: '-0.15***', sub: '-0.25*', dRho: -0.09, nFull: '1,979', nSub: '99' },
    ],
  },
]
