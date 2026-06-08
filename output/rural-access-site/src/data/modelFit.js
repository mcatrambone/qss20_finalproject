// Incremental WLS model sequence. Values transcribed verbatim from
// r2_table_primary_allcause.tex (primary outcome) and
// r2_table_specialist_outcomes.tex (supplementary cause-specific outcomes).
// Adj R2 = adjusted R-squared; dR2 = change vs Model 1 (the covariate baseline);
// partialR2 = partial R-squared attributable to the access score; cvR2 = 5-fold
// cross-validated R-squared; aic = Akaike Information Criterion.

export const modelLabels = {
  M0: 'RUCC Code only',
  M1: '+ Age (% under 65) + State FE',
  M2: '+ Provider density',
  M3: '+ E2SFCA access score',
  M4: '+ Density + access score',
}

// PRIMARY OUTCOME — all-cause mortality (the headline table)
export const primaryAllCause = [
  { model: 'Model 0', predictors: 'RUCC Code', adjR2: 0.350, dR2: null, partialR2: null, cvR2: 0.349, aic: '45,879' },
  { model: 'Model 1', predictors: 'RUCC + Age + State FE', adjR2: 0.715, dR2: null, partialR2: null, cvR2: 0.688, aic: '43,400' },
  { model: 'Model 2', predictors: '+ PCP density', adjR2: 0.730, dR2: 0.015, partialR2: null, cvR2: 0.705, aic: '43,229' },
  { model: 'Model 3', predictors: '+ Primary access score', adjR2: 0.718, dR2: 0.003, partialR2: 0.011, cvR2: 0.691, aic: '43,369' },
  { model: 'Model 4', predictors: '+ Density + access score', adjR2: 0.733, dR2: 0.019, partialR2: 0.012, cvR2: 0.707, aic: '43,192' },
]

// SUPPLEMENTARY — cause-specific outcomes (IHD, Stroke, Respiratory)
export const specialistOutcomes = [
  // IHD
  { outcome: 'IHD', model: 'Model 1', predictors: 'RUCC + Age + State FE', adjR2: 0.589, dR2: null, partialR2: null, cvR2: 0.560 },
  { outcome: 'IHD', model: 'Model 2', predictors: '+ Cardiologist density', adjR2: 0.591, dR2: 0.002, partialR2: null, cvR2: 0.559 },
  { outcome: 'IHD', model: 'Model 4', predictors: '+ Density + access', adjR2: 0.592, dR2: 0.003, partialR2: 0.002, cvR2: 0.561 },
  // Stroke
  { outcome: 'Stroke', model: 'Model 1', predictors: 'RUCC + Age + State FE', adjR2: 0.606, dR2: null, partialR2: null, cvR2: 0.503 },
  { outcome: 'Stroke', model: 'Model 2', predictors: '+ EM physician density', adjR2: 0.607, dR2: 0.001, partialR2: null, cvR2: 0.502 },
  { outcome: 'Stroke', model: 'Model 4', predictors: '+ Density + access', adjR2: 0.606, dR2: 0.001, partialR2: 0.000, cvR2: 0.498 },
  // Respiratory
  { outcome: 'Respiratory', model: 'Model 1', predictors: 'RUCC + Age + State FE', adjR2: 0.647, dR2: null, partialR2: null, cvR2: 0.638 },
  { outcome: 'Respiratory', model: 'Model 2', predictors: '+ EM physician density', adjR2: 0.676, dR2: 0.028, partialR2: null, cvR2: 0.657 },
  { outcome: 'Respiratory', model: 'Model 4', predictors: '+ Density + access', adjR2: 0.677, dR2: 0.029, partialR2: 0.002, cvR2: 0.657 },
]
