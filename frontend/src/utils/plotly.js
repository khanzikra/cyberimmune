let plotlyLoaded = false

export async function loadPlotly() {
  if (plotlyLoaded) return window.Plotly
  const Plotly = await import('plotly.js-dist-min')
  window.Plotly = Plotly.default
  plotlyLoaded = true
  return window.Plotly
}