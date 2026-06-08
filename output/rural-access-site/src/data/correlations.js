// Partial Spearman rho between each access measure and each mortality outcome.
// Residualised on % population under 65 and state fixed effects.
// Transcribed from access_mortality_relevant_correlations.png.
// Only statistically significant (***p<0.001) cells are populated; blanks are
// non-significant / not shown in the source figure.

export const outcomes = [
  'All-cause mortality',
  'IHD mortality',
  'Respiratory mortality',
  'Stroke mortality',
]

export const measures = [
  'Cardiologists per 10k',
  'Cardiology access score',
  'EM physicians per 10k',
  'Emergency access score',
  'PCPs per 10k',
  'Primary access score',
  'RUCC Code',
]

// rho keyed by `${measure}|${outcome}`. Each value: { rho, sig }
export const correlations = {
  'Cardiologists per 10k|IHD mortality': { rho: -0.17, sig: '***' },
  'Cardiology access score|IHD mortality': { rho: -0.12, sig: '***' },

  'EM physicians per 10k|Respiratory mortality': { rho: -0.34, sig: '***' },
  'EM physicians per 10k|Stroke mortality': { rho: -0.15, sig: '***' },

  'Emergency access score|Respiratory mortality': { rho: -0.17, sig: '***' },
  'Emergency access score|Stroke mortality': { rho: -0.12, sig: '***' },

  'PCPs per 10k|All-cause mortality': { rho: -0.17, sig: '***' },
  'Primary access score|All-cause mortality': { rho: -0.11, sig: '***' },

  'RUCC Code|All-cause mortality': { rho: -0.36, sig: '***' },
  'RUCC Code|IHD mortality': { rho: -0.31, sig: '***' },
  'RUCC Code|Respiratory mortality': { rho: -0.37, sig: '***' },
  'RUCC Code|Stroke mortality': { rho: -0.21, sig: '***' },
}
