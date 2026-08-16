/* Bull Band — gameday promo, 19s, built on animations-v3 */
const {
  CompositionStage,
  useComposition,
  Shot,
  Captions,
  Easing,
  animate
} = window;
const {
  useTweaks,
  TweaksPanel,
  TweakSection,
  TweakToggle
} = window;
const GOLD = '#E8B23A',
  PALE = '#F7DFA4',
  DEEP = '#8A6A1E',
  BONE = '#F4F2ED',
  VOID = '#0B0B0D',
  GREY = '#A5A19A';
const BAND = '/assets/bull-band.webp';
const COIN = '/assets/bull-coin.webp';
const HEXURI = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='27.712' height='48' viewBox='0 0 27.712 48'%3E%3Cg fill='none' stroke='%23E8B23A' stroke-width='1'%3E%3Cpath d='M13.856,8 L27.712,16 L27.712,32 L13.856,40 L0,32 L0,16 Z'/%3E%3Cpath d='M0,-16 L13.856,-8 L13.856,8 L0,16 L-13.856,8 L-13.856,-8 Z'/%3E%3Cpath d='M0,32 L13.856,40 L13.856,56 L0,64 L-13.856,56 L-13.856,40 Z'/%3E%3Cpath d='M27.712,-16 L41.568,-8 L41.568,8 L27.712,16 L13.856,8 L13.856,-8 Z'/%3E%3Cpath d='M27.712,32 L41.568,40 L41.568,56 L27.712,64 L13.856,56 L13.856,40 Z'/%3E%3C/g%3E%3C/svg%3E";

/* exactly three motion helpers — all easing lives here */
const MOTION = {
  enter: function (t0, d) {
    d = d || 0.6;
    return function (T) {
      var p = animate({
        from: 0,
        to: 1,
        start: t0,
        end: t0 + d,
        ease: Easing.easeOutCubic
      })(T);
      return {
        opacity: p,
        transform: 'translateY(' + (26 * (1 - p)).toFixed(2) + 'px)'
      };
    };
  },
  pop: function (t0, d) {
    d = d || 0.6;
    return function (T) {
      var s = animate({
        from: 2.6,
        to: 1,
        start: t0,
        end: t0 + d,
        ease: Easing.easeOutBack
      })(T);
      var o = animate({
        from: 0,
        to: 1,
        start: t0,
        end: t0 + d * 0.45,
        ease: Easing.easeOutCubic
      })(T);
      return {
        opacity: o,
        transform: 'scale(' + s.toFixed(4) + ')'
      };
    };
  },
  run: function (t0, t1, ease) {
    return function (T) {
      return animate({
        from: 0,
        to: 1,
        start: t0,
        end: t1,
        ease: ease || Easing.linear
      })(T);
    };
  }
};

/* candle chart data — one red pullback candle in each leg, net up-only */
const GAINS = [38, 26, 44, 18, -22, 52, 30, 24, -16, 58, 36, 42, 28, 64];
const OPENS = function () {
  var a = [],
    acc = 40;
  for (var i = 0; i < GAINS.length; i++) {
    a.push(acc);
    acc += GAINS[i];
  }
  return a;
}();
function CandleChart(props) {
  var T = props.T,
    t0 = props.t0,
    S = 1.15,
    BASE = 424;
  return /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 1600 440",
    style: {
      position: 'absolute',
      left: 60,
      right: 60,
      bottom: 30,
      width: 1800,
      height: 495,
      opacity: 0.9
    }
  }, GAINS.map(function (g, i) {
    var p = MOTION.run(t0 + i * 0.18, t0 + i * 0.18 + 0.5, Easing.easeOutCubic)(props.T);
    if (p <= 0) return null;
    var open = OPENS[i],
      up = g >= 0;
    var bodyH = Math.abs(g) * S * p,
      x = i * 112 + 20;
    var yOpen = BASE - open * S;
    var y = up ? yOpen - bodyH : yOpen;
    var wick = 16 * S * p;
    var cx = x + 23;
    return /*#__PURE__*/React.createElement("g", {
      key: i
    }, /*#__PURE__*/React.createElement("line", {
      x1: cx,
      x2: cx,
      y1: y - wick,
      y2: y + bodyH + wick,
      stroke: PALE,
      strokeWidth: "3",
      opacity: "0.55"
    }), /*#__PURE__*/React.createElement("rect", {
      x: x,
      y: y,
      width: "46",
      height: Math.max(bodyH, 2),
      fill: up ? GOLD : DEEP
    }));
  }));
}
function Chip(props) {
  return /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      display: 'flex',
      alignItems: 'center',
      gap: 20,
      border: '1px solid rgba(232,178,58,.4)',
      background: 'rgba(0,0,0,.5)',
      padding: '17px 24px'
    }, props.anim)
  }, /*#__PURE__*/React.createElement("svg", {
    width: "26",
    height: "30",
    viewBox: "0 0 26 30"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M13 1.5L24.5 8.25V21.75L13 28.5L1.5 21.75V8.25Z",
    fill: "none",
    stroke: GOLD,
    strokeWidth: "2"
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      font: "700 26px 'JetBrains Mono', monospace",
      letterSpacing: '0.16em',
      color: GOLD
    }
  }, props.name), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 5,
      font: "500 15px 'JetBrains Mono', monospace",
      letterSpacing: '0.14em',
      color: GREY
    }
  }, props.sub)));
}
function Piece() {
  var c = useComposition(),
    T = c.T,
    CUES = c.CUES,
    total = c.authoredTotal;
  var tOpen = CUES['Cold Open'],
    tFlex = CUES['Product Flex'],
    tBuild = CUES['The Build'],
    tRun = CUES['Bull Run'],
    tEnd = CUES['End Card'];
  var flexP = MOTION.run(tFlex, tBuild, Easing.easeInOutSine)(T);
  var buildP = MOTION.run(tBuild, tRun, Easing.easeInOutSine)(T);
  var runFade = 1 - MOTION.run(tRun + 1.95, tRun + 2.15)(T);
  var heroP = MOTION.run(tRun, tEnd, Easing.easeInOutSine)(T);
  var blackIn = 1 - MOTION.run(tOpen, tOpen + 0.35)(T);
  var blackOut = MOTION.run(total - 0.55, total - 0.05)(T);
  var duck = Math.max(1 - MOTION.run(tFlex - 0.3, tFlex + 0.2)(T), MOTION.run(tEnd - 0.3, tEnd + 0.2)(T));
  var chips = [['SPACER MESH', 'OPEN-CELL FABRIC'], ['BREATHABLE', 'WICKS AND VENTS'], ['85A–90A TPU', 'BULL BUTTON BADGE'], ['HAND SEWN', 'FOR DURABILITY'], ['BUILT TO RUN', 'FLEXIBLE · LIGHTWEIGHT']];
  return /*#__PURE__*/React.createElement("div", {
    "data-screen-label": 't=' + Math.floor(T) + 's',
    style: {
      position: 'absolute',
      inset: 0,
      background: VOID,
      overflow: 'hidden',
      fontFamily: 'Archivo, system-ui, sans-serif'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'radial-gradient(60% 55% at 50% 34%, rgba(232,178,58,' + ((0.10 + 0.05 * Math.sin(T * 0.8)) * (1 - 0.85 * duck)).toFixed(3) + '), transparent 70%)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      opacity: 0.055 * (1 - 0.9 * duck),
      backgroundImage: 'url("' + HEXURI + '")',
      backgroundSize: '42px 72.7px',
      backgroundPosition: '0 ' + (T * 10 % 72.7).toFixed(2) + 'px'
    }
  }), /*#__PURE__*/React.createElement(Shot, {
    from: tOpen,
    to: tFlex
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      top: '4%',
      display: 'flex',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: COIN,
    alt: "",
    style: Object.assign({
      width: 700,
      maskImage: 'radial-gradient(closest-side, black 55%, transparent 78%)',
      WebkitMaskImage: 'radial-gradient(closest-side, black 55%, transparent 78%)',
      filter: 'drop-shadow(0 30px 90px rgba(232,178,58,.28)) blur(' + (12 * (1 - MOTION.run(tOpen + 0.3, tOpen + 0.85)(T))).toFixed(1) + 'px)'
    }, MOTION.pop(tOpen + 0.3, 0.6)(T))
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      top: '51%',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      font: '900 168px/0.95 Archivo, sans-serif',
      color: BONE,
      letterSpacing: '-0.03em'
    }, MOTION.pop(tOpen + 1.05, 0.55)(T))
  }, "BULL BAND", /*#__PURE__*/React.createElement("span", {
    style: {
      color: GOLD
    }
  }, ".")), /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      marginTop: 20,
      font: '900 56px Archivo, sans-serif',
      color: GOLD,
      letterSpacing: '0.02em'
    }, MOTION.enter(tOpen + 1.85)(T))
  }, "BULL-GRADE SIGNAL."))), /*#__PURE__*/React.createElement(Shot, {
    from: tFlex,
    to: tBuild
  }, /*#__PURE__*/React.createElement("img", {
    src: BAND,
    alt: "",
    style: {
      position: 'absolute',
      inset: 0,
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      transformOrigin: '50% 30%',
      transform: 'scale(1.72) translate(' + (4 - 8 * flexP).toFixed(2) + '%, ' + (2 - 2 * flexP).toFixed(2) + '%)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(180deg, rgba(11,11,13,.3), transparent 30%, transparent 60%, rgba(11,11,13,.85))'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      position: 'absolute',
      left: 70,
      top: 58,
      font: "700 22px 'JetBrains Mono', monospace",
      letterSpacing: '0.22em',
      color: GOLD
    }, MOTION.enter(tFlex + 0.3)(T))
  }, "BULLPRINT LAB \xB7 GAMEDAY")), /*#__PURE__*/React.createElement(Shot, {
    from: tBuild,
    to: tRun
  }, /*#__PURE__*/React.createElement("img", {
    src: BAND,
    alt: "",
    style: {
      position: 'absolute',
      inset: 0,
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      objectPosition: '20% 50%',
      transformOrigin: '30% 50%',
      transform: 'scale(' + (1.18 + 0.08 * buildP).toFixed(3) + ')'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(90deg, transparent 26%, rgba(11,11,13,.55) 48%, rgba(11,11,13,.94) 64%)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: '58%',
      right: '5%',
      top: 110
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      font: "700 21px 'JetBrains Mono', monospace",
      letterSpacing: '0.24em',
      color: DEEP,
      marginBottom: 30
    }, MOTION.enter(tBuild + 0.25)(T))
  }, "THE BUILD \u2014 BULL BAND"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 17
    }
  }, chips.map(function (ch, i) {
    return /*#__PURE__*/React.createElement(Chip, {
      key: i,
      name: ch[0],
      sub: ch[1],
      anim: MOTION.enter(tBuild + 0.55 + i * 0.72)(T)
    });
  })))), /*#__PURE__*/React.createElement(Shot, {
    from: tRun,
    to: tEnd
  }, /*#__PURE__*/React.createElement(CandleChart, {
    T: T,
    t0: tRun + 0.2
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 90,
      top: 150,
      opacity: runFade
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      font: '900 108px/1.02 Archivo, sans-serif',
      color: BONE,
      letterSpacing: '-0.03em'
    }, MOTION.enter(tRun + 0.4)(T))
  }, "DON'T JUST WATCH", /*#__PURE__*/React.createElement("br", null), "THE BULL RUN.")), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      top: '30%',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      font: '900 250px Archivo, sans-serif',
      color: GOLD,
      letterSpacing: '-0.02em',
      textShadow: '0 24px 90px rgba(232,178,58,.3)'
    }, MOTION.pop(tRun + 2.2, 0.6)(T))
  }, "WEAR IT."))), /*#__PURE__*/React.createElement(Shot, {
    from: tEnd
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      top: 70,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: COIN,
    alt: "",
    style: Object.assign({
      width: 470,
      maskImage: 'radial-gradient(closest-side, black 55%, transparent 78%)',
      WebkitMaskImage: 'radial-gradient(closest-side, black 55%, transparent 78%)',
      filter: 'drop-shadow(0 24px 70px rgba(232,178,58,.24))'
    }, MOTION.pop(tEnd + 0.15, 0.55)(T))
  }), /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      marginTop: 34,
      font: '900 86px Archivo, sans-serif',
      color: BONE,
      letterSpacing: '-0.02em'
    }, MOTION.enter(tEnd + 0.55)(T))
  }, "BULLPRINT LAB"), /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      marginTop: 22,
      width: 340,
      height: 1,
      background: 'linear-gradient(90deg, transparent, ' + GOLD + ', transparent)'
    }, MOTION.enter(tEnd + 0.75)(T))
  }), /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      marginTop: 22,
      font: "700 27px 'JetBrains Mono', monospace",
      letterSpacing: '0.3em',
      color: GOLD
    }, MOTION.enter(tEnd + 0.95)(T))
  }, "BULLPRINTLAB.COM"), /*#__PURE__*/React.createElement("div", {
    style: Object.assign({
      marginTop: 26,
      font: "700 19px 'JetBrains Mono', monospace",
      letterSpacing: '0.2em',
      color: GREY,
      border: '1px solid rgba(255,255,255,.25)',
      padding: '14px 26px'
    }, MOTION.enter(tEnd + 1.15)(T))
  }, "GET YOUR BULL BAND \u2192"))), /*#__PURE__*/React.createElement(Captions, {
    style: {
      font: "700 33px 'JetBrains Mono', monospace",
      color: PALE,
      letterSpacing: '0.14em',
      textShadow: '0 2px 26px rgba(0,0,0,.85)'
    },
    items: [{
      at: tFlex + 0.4,
      text: 'ENGINEERED COMFORT.'
    }, {
      at: tFlex + 1.8,
      text: 'BULL-GRADE SIGNAL.'
    }, {
      at: tFlex + 3.15,
      until: tBuild - 0.1,
      text: 'WHEN THE GAME STARTS… YOU ALREADY LOCKED IN.'
    }]
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      background: 'radial-gradient(120% 120% at 50% 50%, transparent 55%, rgba(0,0,0,.5))'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      background: '#000',
      opacity: Math.max(blackIn, blackOut)
    }
  }));
}
function BullBandPromo() {
  var tw = useTweaks(window.TWEAK_DEFAULTS),
    t = tw[0],
    setTweak = tw[1];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      minHeight: '100vh',
      display: 'grid',
      placeItems: 'center',
      background: '#060608',
      padding: '28px 0',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement(CompositionStage, {
    width: 1920,
    height: 1080,
    scenes: window.OM_SCENES,
    playback: window.OM_PLAYBACK,
    bg: "#0B0B0D"
  }, /*#__PURE__*/React.createElement(Piece, null)), /*#__PURE__*/React.createElement(TweaksPanel, null, /*#__PURE__*/React.createElement(TweakSection, {
    label: "Timeline"
  }), /*#__PURE__*/React.createElement(TweakToggle, {
    label: "Motion editor",
    value: t.motionEditor,
    onChange: function (v) {
      setTweak('motionEditor', v);
    }
  })));
}
window.BullBandPromo = BullBandPromo;