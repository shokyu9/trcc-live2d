const engine = new URLSearchParams(location.search).get('engine') || 'classic';
const pixiModule = engine === 'lipsync' ? await import('pixi7') : await import('pixi.js');
const PIXI = pixiModule.default || pixiModule;
window.PIXI = PIXI;

const { Live2DModel } = engine === 'lipsync'
  ? await import('pixi-live2d-display-lipsyncpatch/cubism4')
  : await import('pixi-live2d-display/cubism4');
Live2DModel.registerTicker(PIXI.Ticker);
const query = new URLSearchParams(location.search);
const width = Number(query.get('width')) || 480;
const height = Number(query.get('height')) || 480;
const app = new PIXI.Application({
  view: document.querySelector('#stage'), width, height, backgroundAlpha: 0,
  preserveDrawingBuffer: true, resolution: 1, antialias: true
});
app.ticker.maxFPS = 12;
PIXI.Ticker.shared.maxFPS = 12;
const model = await Live2DModel.from('/model/' + encodeURIComponent(query.get('model')), { ticker: PIXI.Ticker.shared });
// Small facial masks need more precision than the SDK's 256px default.
model.internalModel.renderer.setClippingMaskBufferSize(1024);
model.anchor.set(.5, .5);
model.scale.set(Math.min(width / model.width, height / model.height) * .92);
model.position.set(width / 2, height / 2);
app.stage.addChild(model);
const baseScale = model.scale.x;
let options = {};
let lastOptions = "";
let lastBand = 'normal';
let currentTemperature = null;
let currentBand = 'normal';
let nextGesture = performance.now() + 12000;
let returnGesture = null;
let returnAt = 0;
let nextBlink = 2500;
const startedAt = performance.now();
function playSafe(group) {
  if (model.internalModel.motionManager.definitions[group]) {
    Promise.resolve(model.motion(group, 0, 3)).catch(() => {});
  }
}
model.internalModel.on('beforeModelUpdate', () => {
  const core = model.internalModel.coreModel;
  const t = (performance.now() - startedAt) / 1000;
  const manual = options.parameters || {};
  const set = (id, value) => { if (!(id in manual)) core.setParameterValueById(id, value); };
  // This model's black-face expression is key1. Neutralize it unless chosen.
  if (options.expression !== '黑脸') set('key1', 0);
  set('NoseNeer', 0);
  if (options.autoActions !== false && !options.motion) {
    if (options.autoSway !== false) {
    const strength = options.idleStrength ?? 1;
    set('ParamAngleX', (Math.sin(t * .37) * 7 + Math.sin(t * .13) * 3) * strength);
    set('ParamAngleY', Math.sin(t * .29) * 4);
    set('ParamAngleZ', Math.sin(t * .23) * 3);
    set('ParamBodyAngleX', Math.sin(t * .19) * 2 * strength);
    }
    if (options.autoBreath !== false) set('ParamBreath', (Math.sin(t * 1.6 * (options.breathSpeed || 1)) + 1) / 2);
    if (t * 1000 > nextBlink + 180) nextBlink = t * 1000 + 2800 + Math.random() * 3500;
    const phase = (t * 1000 - nextBlink) / 180;
    const eye = phase >= 0 && phase <= 1 ? Math.abs(phase * 2 - 1) : 1;
    if (options.autoBlink !== false) { set('ParamEyeLOpen', eye); set('ParamEyeROpen', eye); }
  }
  for (const [id,value] of Object.entries(manual)) core.setParameterValueById(id, Number(value));
});
app.ticker.add(() => {
  model.scale.set(baseScale * (options.scale ?? 1));
  model.position.set(width / 2 + (options.x ?? 0), height / 2 + (options.y ?? 0));
  const now = performance.now();
  if (options.autoActions !== false && !options.motion) {
    if (returnGesture && now > returnAt) { playSafe(returnGesture); returnGesture = null; }
    if (now > nextGesture && !returnGesture) {
      const gestures = currentBand === 'hot'
        ? [['竖手指切出来动画', '竖手指切回默认']]
        : currentBand === 'warm'
        ? [['默认手切举手', '举手切默认手']]
        : [['默认手切举手', '举手切默认手'], ['狗尾草切换出来', '狗尾草切回默认手']];
      const [gesture, back] = gestures[Math.floor(Math.random() * gestures.length)];
      playSafe(gesture); returnGesture = back; returnAt = now + 6000;
      nextGesture = now + 24000 + Math.random() * 20000;
    }
  }
  const customCore = model.internalModel?.coreModel;
  for (const [id, value] of Object.entries(options.parameters || {})) {
    customCore?.setParameterValueById(id, Number(value));
  }
  for (const [id, value] of Object.entries(options.parts || {})) {
    const index = customCore?._partIds?.indexOf(id);
    if (index >= 0) customCore._partOpacities[index] = Number(value);
  }
  if (currentTemperature === null || options.temperature === false) return;
  const core = model.internalModel?.coreModel;
  if (core?.setParameterValueById) {

    core.setParameterValueById('ParamCheek', currentBand === 'hot' ? 1 : currentBand === 'warm' ? .5 : 0);
  }
}, undefined, PIXI.UPDATE_PRIORITY.LOW);
window.setTelemetry = ({ temperature, warm = 55, hot = 75, options: incoming = {} }) => {
  options = incoming;
  app.ticker.maxFPS = Math.max(4, Math.min(30, options.fps || 8));
  PIXI.Ticker.shared.maxFPS = app.ticker.maxFPS;
  const signature = JSON.stringify([options.motion, options.expression]);
  if (signature !== lastOptions) {
    lastOptions = signature;
    if (options.expression) model.expression(options.expression);
    if (options.motion) model.motion(options.motion, 0, 3);
  }
  if (typeof temperature !== 'number' || !Number.isFinite(temperature)) return;
  const band = temperature >= hot ? 'hot' : temperature >= warm ? 'warm' : 'normal';
  currentTemperature = temperature;
  currentBand = band;
  if (options.temperature === false || options.expression) return;
  if (band !== lastBand) {
    lastBand = band;
    if (band === 'normal') {
      model.internalModel?.motionManager?.expressionManager?.resetExpression();
    } else {
      try { Promise.resolve(model.expression(band)).catch(() => {}); } catch (_) { /* optional expression */ }
      try { Promise.resolve(model.motion(band)).catch(() => {}); } catch (_) { /* optional motion */ }
    }
  }
};
window.captureFrame = () => document.querySelector('#stage').toDataURL('image/png').split(',')[1];
window.rendererReady = true;
