DASHBOARD_HTML = """
<!DOCTYPE html>
<html class="dark" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>ZEN AI Dashboard</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@300;400;500&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 24;
        }
        .glass-panel {
            background: rgba(12, 19, 34, 0.4);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 221, 221, 0.2);
        }
        .glow-cyan { box-shadow: 0 0 15px rgba(0, 221, 221, 0.3); }
        .glow-purple { box-shadow: 0 0 15px rgba(221, 183, 255, 0.3); }
        .scan-line {
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0, 251, 251, 0.5), transparent);
            position: absolute;
            animation: scan 4s linear infinite;
        }
        @keyframes scan {
            0% { top: 0; }
            100% { top: 100%; }
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(0, 251, 251, 0.2); border-radius: 10px; }
    </style>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    "colors": {
                        "surface-container": "#191f2f",
                        "on-primary-container": "#007070",
                        "tertiary-fixed": "#ffe088",
                        "outline-variant": "#3a4a49",
                        "tertiary": "#ffffff",
                        "secondary-fixed-dim": "#ddb7ff",
                        "primary-container": "#00fbfb",
                        "primary-fixed": "#00fbfb",
                        "background": "#0c1322",
                        "surface": "#0c1322",
                        "surface-tint": "#00dddd",
                        "error": "#ffb4ab",
                        "surface-variant": "#2e3445",
                        "tertiary-fixed-dim": "#e9c349",
                        "surface-container-lowest": "#070e1d",
                        "inverse-on-surface": "#2a3041",
                        "primary-fixed-dim": "#00dddd",
                        "surface-container-low": "#151b2b",
                        "inverse-surface": "#dce2f8",
                        "surface-bright": "#32394a",
                        "primary": "#ffffff",
                        "surface-container-high": "#232a3a",
                        "secondary": "#ddb7ff",
                        "surface-container-highest": "#2e3445",
                        "secondary-fixed": "#f0dbff"
                    },
                    "fontFamily": {
                        "headline-md": ["Sora"],
                        "body-md": ["Inter"],
                        "data-label": ["Space Mono"],
                        "display-lg": ["Sora"],
                        "code-sm": ["Space Mono"],
                        "body-lg": ["Inter"]
                    }
                },
            },
        }
    </script>
</head>
<body class="bg-background text-[#dce2f8] font-body-md selection:bg-primary-container selection:text-on-primary-container m-0 p-0 overflow-x-hidden">

<!-- MAIN CONTENT CANVAS -->
<main class="w-full pt-4 pb-12 px-[40px] min-h-screen">
<!-- HERO SECTION -->
<section class="relative mt-2 rounded-xl overflow-hidden border border-outline-variant/20 h-[320px] flex items-center px-12 group">
<!-- STITCH_SHADER_START:ANIMATION_2 -->
<div class="absolute inset-0 w-full h-full -z-10" style="display:block;">
<canvas id="shader-canvas-ANIMATION_2" style="display:block;width:100%;height:100%"></canvas>
<script>
(function() {
  const canvas = document.getElementById('shader-canvas-ANIMATION_2');
  function syncSize() {
    const w = canvas.clientWidth || 1280;
    const h = canvas.clientHeight || 720;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
  }
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(syncSize).observe(canvas);
  syncSize();
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  if (!gl) return;
  const vs = `attribute vec2 a_position; varying vec2 v_texCoord; void main() { v_texCoord = a_position * 0.5 + 0.5; gl_Position = vec4(a_position, 0.0, 1.0); }`;
  const fs = `precision highp float; uniform float u_time; uniform vec2 u_resolution; varying vec2 v_texCoord;
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p) { vec2 i = floor(p); vec2 f = fract(p); float a = hash(i); float b = hash(i + vec2(1.0, 0.0)); float c = hash(i + vec2(0.0, 1.0)); float d = hash(i + vec2(1.0, 1.0)); vec2 u = f * f * (3.0 - 2.0 * u); return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y; }
float fbm(vec2 p) { float v = 0.0; float a = 0.5; vec2 shift = vec2(100.0); mat2 rot = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.5)); for (int i = 0; i < 6; ++i) { v += a * noise(p); p = rot * p * 2.0 + shift; a *= 0.5; } return v; }
void main() { vec2 uv = v_texCoord; vec2 p = (uv - 0.5) * 2.0; p.x *= u_resolution.x / u_resolution.y; float t = u_time * 0.05; vec2 p1 = p * 1.5 + vec2(sin(t), cos(t)) * 0.5; vec2 p2 = p * 2.0 - vec2(cos(t * 1.1), sin(t * 0.9)) * 0.4; float n1 = fbm(p1 + fbm(p1 + t)); float n2 = fbm(p2 + fbm(p2 - t * 0.5)); vec3 col1 = vec3(0.0, 0.05, 0.15); vec3 col2 = vec3(0.0, 0.4, 0.4); vec3 col3 = vec3(0.4, 0.1, 0.5); vec3 color = col1; color = mix(color, col2, n1 * 0.8); color = mix(color, col3, n2 * 0.6); float stars = pow(hash(uv + floor(u_time * 0.01)), 500.0) * 2.0; color += stars; color *= 1.2 - length(p) * 0.5; gl_FragColor = vec4(color, 1.0); }`;
  function cs(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }
  const prog = gl.createProgram(); gl.attachShader(prog, cs(gl.VERTEX_SHADER, vs)); gl.attachShader(prog, cs(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(prog); gl.useProgram(prog);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  const pos = gl.getAttribLocation(prog, 'a_position'); gl.enableVertexAttribArray(pos); gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);
  const uTime = gl.getUniformLocation(prog, 'u_time'); const uRes = gl.getUniformLocation(prog, 'u_resolution');
  function render(t) { if (typeof ResizeObserver === 'undefined') syncSize(); gl.viewport(0, 0, canvas.width, canvas.height); if (uTime) gl.uniform1f(uTime, t * 0.001); if (uRes) gl.uniform2f(uRes, canvas.width, canvas.height); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); requestAnimationFrame(render); }
  render(0);
})();
</script>
</div>
<!-- STITCH_SHADER_END -->
<div class="absolute inset-0 bg-gradient-to-r from-background via-background/40 to-transparent"></div>
<div class="relative z-10 max-w-2xl">
<h2 class="font-display-lg text-[48px] font-bold text-primary mb-4 drop-shadow-[0_4px_4px_rgba(0,0,0,0.5)]">Welcome back, Creator.</h2>
<p class="font-body-lg text-[18px] text-[#b9cac9] mb-8 leading-relaxed">
    The archives currently contain <span class="text-primary-fixed font-bold">[[UNIVERSES]] universes</span>, <span class="text-secondary font-bold">[[CHARACTERS]] characters</span> and <span class="text-primary-fixed-dim font-bold">[[TOTAL_ENTITIES]] total entities</span>. 
    Your multiversal timeline is stable.
</p>
<div class="flex gap-4">
<button class="px-6 py-2 glass-panel hover:bg-primary/10 transition-all font-data-label text-[12px] uppercase tracking-widest border-primary/30 group-hover:border-primary text-white">Resynchronize Core</button>
</div>
</div>
<!-- AI STATUS ORB -->
<div class="absolute right-12 top-1/2 -translate-y-1/2 flex flex-col items-center">
<div class="w-48 h-48 rounded-full glass-panel border-primary/20 flex items-center justify-center relative glow-cyan">
<div class="scan-line rounded-full overflow-hidden"></div>
<div class="w-32 h-32 rounded-full bg-gradient-to-br from-primary-fixed-dim/20 to-transparent blur-xl animate-pulse"></div>
<div class="absolute inset-0 flex flex-col items-center justify-center">
<span class="material-symbols-outlined text-primary-fixed-dim scale-[2.5]" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
<p class="mt-6 font-data-label text-[12px] text-primary-fixed-dim tracking-[0.2em] font-bold">[[OLLAMA_STATUS]]</p>
</div>
</div>
<div class="mt-4 flex gap-2">
<div class="w-2 h-2 rounded-full bg-primary-fixed glow-cyan"></div>
<div class="w-2 h-2 rounded-full bg-primary-fixed/20"></div>
<div class="w-2 h-2 rounded-full bg-primary-fixed/20"></div>
</div>
</div>
</section>

<!-- STATISTICS GRID -->
<section class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
<!-- Stat Cards -->
<div class="glass-panel p-5 rounded-lg border-l-2 border-primary group hover:border-primary/50 transition-all">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined text-primary">public</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Universes</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-primary">[[UNIVERSES_PAD]]</h3>
<div class="w-full bg-outline-variant/10 h-[2px] mt-4 overflow-hidden">
<div class="bg-primary h-full w-2/3 shadow-[0_0_8px_rgba(255,255,255,0.5)]"></div>
</div>
</div>

<div class="glass-panel p-5 rounded-lg border-l-2 border-secondary group hover:border-secondary/50 transition-all">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined text-secondary">person</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Characters</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-secondary">[[CHARACTERS_PAD]]</h3>
<div class="w-full bg-outline-variant/10 h-[2px] mt-4 overflow-hidden">
<div class="bg-secondary h-full w-[45%] shadow-[0_0_8px_rgba(221,183,255,0.5)]"></div>
</div>
</div>

<div class="glass-panel p-5 rounded-lg border-l-2 border-tertiary-fixed-dim group hover:border-tertiary-fixed-dim/50 transition-all">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined text-tertiary-fixed-dim">groups</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Factions</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-tertiary-fixed-dim">[[FACTIONS_PAD]]</h3>
<div class="w-full bg-outline-variant/10 h-[2px] mt-4 overflow-hidden">
<div class="bg-tertiary-fixed-dim h-full w-1/2"></div>
</div>
</div>

<div class="glass-panel p-5 rounded-lg border-l-2 border-primary-container group hover:border-primary-container/50 transition-all">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined text-primary-container">map</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Locations</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-primary-container">[[LOCATIONS_PAD]]</h3>
<div class="w-full bg-outline-variant/10 h-[2px] mt-4 overflow-hidden">
<div class="bg-primary-container h-full w-3/4"></div>
</div>
</div>

<!-- Row 2 Stats -->
<div class="glass-panel p-5 rounded-lg border-l-2 border-[#d6a9ff]/50 group">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined">auto_awesome</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Artifacts</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-[#dce2f8]">[[ARTIFACTS_PAD]]</h3>
</div>

<div class="glass-panel p-5 rounded-lg border-l-2 border-[#d6a9ff]/50 group">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined">menu_book</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Stories</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-[#dce2f8]">[[STORIES_PAD]]</h3>
</div>

<div class="glass-panel p-5 rounded-lg border-l-2 border-[#d6a9ff]/50 group">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined">event</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Events</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-[#dce2f8]">[[EVENTS_PAD]]</h3>
</div>

<div class="glass-panel p-5 rounded-lg border-l-2 border-[#d6a9ff]/50 group">
<div class="flex justify-between items-start mb-2">
<span class="material-symbols-outlined">share</span>
</div>
<p class="text-[#839493] font-data-label text-[10px] uppercase tracking-widest">Relationships</p>
<h3 class="text-3xl font-headline-md font-bold mt-1 text-[#dce2f8]">[[RELATIONSHIPS_PAD]]</h3>
</div>
</section>

<!-- TWO COLUMN LAYOUT: LORE & STATUS -->
<div class="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
<!-- LEFT: UNIVERSE OVERVIEW -->
<div class="lg:col-span-2 space-y-6">
<!-- ROOT ENTITIES SECTION -->
<div class="space-y-4">
<h2 class="font-headline-md text-2xl text-primary mt-2 flex items-center gap-3">
<span class="material-symbols-outlined text-secondary">all_inclusive</span>
                        Top Root Entities
                    </h2>
<div class="glass-panel rounded-xl p-1 flex flex-col gap-[2px]">
[[ROOT_ENTITIES_HTML]]
</div>
</div>
</div>

<!-- RIGHT: SYSTEM STATUS & ACTIVITY -->
<div class="space-y-8">
<!-- SYSTEM STATUS PANEL -->
<div class="glass-panel rounded-xl p-6 border-t-2 border-primary-fixed-dim relative">
<div class="scan-line"></div>
<h3 class="font-data-label text-[12px] text-primary-fixed-dim mb-6 flex items-center gap-2 tracking-widest">
<span class="material-symbols-outlined text-sm">settings_input_component</span>
                        SYSTEM CORE STATUS
                    </h3>
<div class="space-y-5">
<div>
<div class="flex justify-between text-[10px] font-data-label mb-1 uppercase tracking-tighter">
<span>AI Engine</span>
<span class="text-primary-fixed">Stable</span>
</div>
<div class="h-1 w-full bg-outline-variant/20 rounded-full overflow-hidden">
<div class="h-full bg-primary-fixed w-[92%] glow-cyan"></div>
</div>
</div>
<div>
<div class="flex justify-between text-[10px] font-data-label mb-1 uppercase tracking-tighter">
<span>Vector Search (FAISS)</span>
<span class="text-primary-fixed">Active // [[FAISS_VECTORS]] vectors</span>
</div>
<div class="h-1 w-full bg-outline-variant/20 rounded-full overflow-hidden">
<div class="h-full bg-primary-fixed w-[100%] glow-cyan"></div>
</div>
</div>
<div>
<div class="flex justify-between text-[10px] font-data-label mb-1 uppercase tracking-tighter">
<span>Database Core</span>
<span class="text-primary-fixed">Connected</span>
</div>
<div class="h-1 w-full bg-outline-variant/20 rounded-full overflow-hidden">
<div class="h-full bg-primary-fixed w-[100%] glow-cyan"></div>
</div>
</div>
</div>
<div class="mt-8 pt-6 border-t border-outline-variant/10">
<div class="flex items-center gap-3">
<div class="w-3 h-3 rounded-full bg-[#007070] animate-pulse shadow-[0_0_10px_#007070]"></div>
<span class="font-code-sm text-[12px] text-[#839493]">All systems nominal. No leaks detected.</span>
</div>
</div>
</div>
</div>
</div>
</main>
<script>
    document.addEventListener('mousemove', (e) => {
        const panels = document.querySelectorAll('.glass-panel');
        const x = (e.clientX / window.innerWidth) - 0.5;
        const y = (e.clientY / window.innerHeight) - 0.5;
        panels.forEach(panel => {
            const speed = 10;
            panel.style.transform = `perspective(1000px) rotateY(${x * speed}deg) rotateX(${y * -speed}deg)`;
        });
    });
    document.addEventListener('mouseleave', () => {
        const panels = document.querySelectorAll('.glass-panel');
        panels.forEach(panel => {
            panel.style.transform = `perspective(1000px) rotateY(0deg) rotateX(0deg)`;
        });
    });
</script>
</body></html>
"""
