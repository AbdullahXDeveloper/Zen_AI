import os
import json
from app.database.db_init import get_session
from app.database.models import RootEntity

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Golden Entity Matrix Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0e17;
            --bg-card: rgba(20, 25, 35, 0.7);
            --gold-primary: #FFD700;
            --gold-glow: rgba(255, 215, 0, 0.4);
            --text-main: #f0f0f0;
            --text-muted: #8892b0;
            --cyan-accent: #00d2ff;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 15% 50%, rgba(255, 215, 0, 0.05), transparent 25%),
                radial-gradient(circle at 85% 30%, rgba(0, 210, 255, 0.05), transparent 25%);
            overflow-x: hidden;
        }

        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 1rem;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(90deg, var(--gold-primary), #ffaa00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-transform: uppercase;
            letter-spacing: 2px;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        h1::before {
            content: '★';
            font-size: 2rem;
            color: var(--gold-primary);
            -webkit-text-fill-color: var(--gold-primary);
            text-shadow: 0 0 15px var(--gold-glow);
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 1.1rem;
        }

        .grid-container {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 2rem;
        }

        @media (max-width: 1024px) {
            .grid-container {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, var(--gold-primary), transparent);
            opacity: 0.5;
        }

        .card-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--gold-primary);
        }

        .entity-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .entity-item {
            display: flex;
            align-items: center;
            padding: 1rem;
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            border-left: 4px solid transparent;
        }

        .entity-item:hover, .entity-item.active {
            background: rgba(255, 215, 0, 0.05);
            border-left-color: var(--gold-primary);
        }

        .entity-icon {
            font-size: 1.5rem;
            margin-right: 15px;
            color: var(--gold-primary);
            text-shadow: 0 0 10px var(--gold-glow);
        }

        .entity-info h3 {
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .entity-info p {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 4px;
        }

        .visualization-area {
            background: radial-gradient(circle at center, rgba(20,25,35,1) 0%, rgba(10,14,23,1) 100%);
            border-radius: 16px;
            border: 1px solid rgba(255,215,0,0.1);
            position: relative;
            min-height: 500px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            box-shadow: inset 0 0 50px rgba(0,0,0,0.5);
        }

        /* Network nodes */
        .node {
            position: absolute;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
            z-index: 10;
        }

        .node-star {
            width: 60px;
            height: 60px;
            clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
            background: var(--bg-dark);
            border: 2px solid var(--gold-primary);
            box-shadow: 0 0 20px var(--gold-glow), inset 0 0 15px var(--gold-glow);
            transition: all 0.3s ease;
            position: relative;
        }

        .node-star::after {
            content: '';
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 80%; height: 80%;
            background: var(--gold-primary);
            clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
            opacity: 0.2;
        }

        .node:hover .node-star, .node.active .node-star {
            transform: scale(1.2);
            background: rgba(255,215,0,0.2);
            box-shadow: 0 0 30px var(--gold-glow), inset 0 0 20px var(--gold-primary);
        }

        .node-label {
            margin-top: 15px;
            font-weight: 600;
            color: var(--gold-primary);
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
            letter-spacing: 1px;
            background: rgba(0,0,0,0.5);
            padding: 4px 10px;
            border-radius: 4px;
            backdrop-filter: blur(4px);
        }

        /* Connections */
        svg.connections {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: 1;
            pointer-events: none;
        }

        .link-dashed {
            stroke: var(--gold-primary);
            stroke-width: 2;
            stroke-dasharray: 8 8;
            opacity: 0.4;
            animation: dash 30s linear infinite;
        }

        @keyframes dash {
            to { stroke-dashoffset: 1000; }
        }

        /* Prime Elements (Universes) */
        .prime-link {
            stroke: var(--cyan-accent);
            stroke-width: 1.5;
            opacity: 0.6;
            stroke-dasharray: 4 4;
            animation: dash 15s linear infinite;
        }
        .prime-label {
            color: var(--cyan-accent);
            font-size: 0.8rem;
            margin-top: 10px;
            background: rgba(0,0,0,0.5);
            padding: 2px 8px;
            border-radius: 4px;
        }
        .hexagon {
            width: 60px;
            height: 69px;
            background: transparent;
            border: 2px solid var(--cyan-accent);
            clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
            transition: all 0.3s ease;
        }
        .node:hover .hexagon, .node.active .hexagon {
            transform: scale(1.2);
            background: rgba(0,210,255,0.2);
            box-shadow: 0 0 30px rgba(0,210,255,0.4), inset 0 0 20px var(--cyan-accent);
        }

        /* Details Panel */
        .details-panel {
            margin-top: 2rem;
            display: none;
            animation: fadeIn 0.4s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .stat-card {
            background: rgba(0,0,0,0.3);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .stat-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-main);
            margin-top: 5px;
        }

    </style>
</head>
<body>

    <div class="dashboard-container">
        <header>
            <div>
                <h1>Golden Entities</h1>
                <p class="subtitle">Single Entity Matrix Observation Dashboard</p>
            </div>
            <div style="text-align: right;">
                <p style="color: var(--gold-primary); font-weight: 600; font-size: 1.2rem;">SYSTEM: SECURE</p>
                <p style="color: var(--text-muted); font-size: 0.9rem;" id="monitor-count">Monitoring Nodes</p>
            </div>
        </header>

        <div class="grid-container">
            <!-- Left Sidebar -->
            <div class="card">
                <h2 class="card-title">Entity Index</h2>
                <ul class="entity-list" id="entity-list-container">
                    <!-- JS will populate this -->
                </ul>
            </div>

            <!-- Main Visualization -->
            <div style="display: flex; flex-direction: column; gap: 2rem;">
                <div class="visualization-area" id="vis-area">
                    <!-- SVG Connections -->
                    <svg class="connections" id="svg-lines">
                        <!-- Lines will be drawn by JS -->
                    </svg>
                    
                    <!-- Nodes will be drawn by JS -->
                </div>

                <!-- Entity Details Panel -->
                <div class="card details-panel" id="details-panel">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h2 class="card-title" id="detail-title" style="margin-bottom: 5px; font-size: 2rem;"></h2>
                            <p id="detail-type" style="color: var(--text-muted);"></p>
                        </div>
                        <div style="padding: 5px 15px; background: rgba(255,215,0,0.1); border: 1px solid var(--gold-primary); border-radius: 20px; color: var(--gold-primary); font-weight: 600; font-size: 0.8rem;">
                            STATUS: ACTIVE
                        </div>
                    </div>
                    
                    <p id="detail-desc" style="margin-top: 1.5rem; line-height: 1.6; color: #ccc;">
                    </p>

                    <div class="stat-grid">
                        <div class="stat-card">
                            <div class="stat-label">Importance Score</div>
                            <div class="stat-value" id="stat-res"></div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Connections</div>
                            <div class="stat-value" id="stat-conn">Linked</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Entity Type</div>
                            <div class="stat-value" style="color: var(--gold-primary)">Root Entity</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Data injected by Python
        const entityData = {ENTITY_DATA_JSON};

        function buildUI() {
            const listContainer = document.getElementById('entity-list-container');
            const visArea = document.getElementById('vis-area');
            const keys = Object.keys(entityData);
            
            document.getElementById('monitor-count').innerText = `Monitoring ${keys.length} Nodes`;

            // Build list
            listContainer.innerHTML = '';
            keys.forEach(k => {
                const data = entityData[k];
                const li = document.createElement('li');
                li.className = 'entity-item';
                li.dataset.id = k;
                
                const icon = data.is_root ? '★' : '⬡';
                
                li.innerHTML = `
                    <div class="entity-icon" style="color: ${data.is_root ? 'var(--gold-primary)' : 'var(--cyan-accent)'}">${icon}</div>
                    <div class="entity-info">
                        <h3>${data.title}</h3>
                        <p>${data.type}</p>
                    </div>
                `;
                li.addEventListener('click', () => selectEntity(k));
                listContainer.appendChild(li);
            });

            // Draw Nodes
            drawNodes(keys);
        }

        function createNodeElement(id, data) {
            const div = document.createElement('div');
            div.className = 'node';
            div.dataset.id = id;
            
            if (data.is_root) {
                const star = document.createElement('div');
                star.className = 'node-star';
                div.appendChild(star);
            } else {
                const hex = document.createElement('div');
                hex.className = 'hexagon';
                div.appendChild(hex);
            }
            
            const label = document.createElement('div');
            label.className = data.is_root ? 'node-label' : 'prime-label';
            label.innerText = data.title;
            
            div.appendChild(label);
            return div;
        }

        function drawNodes(keys) {
            const visArea = document.getElementById('vis-area');
            // Remove old nodes
            visArea.querySelectorAll('.node').forEach(n => n.remove());

            if(keys.length === 0) return;

            const rootKeys = keys.filter(k => entityData[k].is_root);
            const uniKeys = keys.filter(k => !entityData[k].is_root);

            // Find center (highest score or first)
            let centerId = rootKeys[0];
            let maxScore = -1;
            rootKeys.forEach(k => {
                if(entityData[k].score > maxScore) {
                    maxScore = entityData[k].score;
                    centerId = k;
                }
            });

            const satellites = rootKeys.filter(k => k !== centerId);

            // Create Center Node
            if (centerId) {
                const centerNode = createNodeElement(centerId, entityData[centerId]);
                centerNode.id = 'node-' + centerId;
                centerNode.style.top = '50%';
                centerNode.style.left = '50%';
                centerNode.style.transform = 'translate(-50%, -50%)';
                centerNode.style.zIndex = '20';
                centerNode.querySelector('.node-star').style.width = '100px';
                centerNode.querySelector('.node-star').style.height = '100px';
                centerNode.querySelector('.node-star').style.borderWidth = '3px';
                visArea.appendChild(centerNode);
            }

            // Create Satellite Root Nodes
            const radius = 200; // 200px radius
            satellites.forEach((id, i) => {
                const node = createNodeElement(id, entityData[id]);
                node.id = 'node-' + id;
                
                const angle = (i / satellites.length) * 2 * Math.PI - Math.PI/2;
                const xOffset = Math.cos(angle) * radius;
                const yOffset = Math.sin(angle) * radius;
                
                node.style.top = `calc(50% + ${yOffset}px)`;
                node.style.left = `calc(50% + ${xOffset}px)`;
                node.style.transform = 'translate(-50%, -50%)';
                
                visArea.appendChild(node);
            });

            // Create Universe Nodes (Hexagons) in an outer circle
            const uniRadius = 350;
            uniKeys.forEach((id, i) => {
                const node = createNodeElement(id, entityData[id]);
                node.id = 'node-' + id;
                
                const angle = (i / uniKeys.length) * 2 * Math.PI - Math.PI/2;
                const xOffset = Math.cos(angle) * uniRadius;
                const yOffset = Math.sin(angle) * uniRadius;
                
                node.style.top = `calc(50% + ${yOffset}px)`;
                node.style.left = `calc(50% + ${xOffset}px)`;
                node.style.transform = 'translate(-50%, -50%)';
                
                visArea.appendChild(node);
            });

            // Reattach listeners
            const nodes = document.querySelectorAll('.node');
            nodes.forEach(node => {
                node.addEventListener('click', () => selectEntity(node.dataset.id));
            });

            drawLines();
        }

        function drawLines() {
            const svg = document.getElementById('svg-lines');
            const vis = document.getElementById('vis-area');
            const visRect = vis.getBoundingClientRect();

            const getCenter = (id) => {
                const el = document.getElementById('node-' + id);
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return {
                    x: rect.left - visRect.left + rect.width / 2,
                    y: rect.top - visRect.top + rect.height / 2
                };
            };

            const keys = Object.keys(entityData);
            if(keys.length === 0) return;

            const rootKeys = keys.filter(k => entityData[k].is_root);
            const uniKeys = keys.filter(k => !entityData[k].is_root);

            let centerId = rootKeys[0];
            let maxScore = -1;
            rootKeys.forEach(k => {
                if(entityData[k].score > maxScore) {
                    maxScore = entityData[k].score;
                    centerId = k;
                }
            });

            const satellites = rootKeys.filter(k => k !== centerId);
            const centerPoint = getCenter(centerId);

            svg.innerHTML = ''; // Clear

            const createLine = (p1, p2, className) => {
                if(!p1 || !p2) return;
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', p1.x);
                line.setAttribute('y1', p1.y);
                line.setAttribute('x2', p2.x);
                line.setAttribute('y2', p2.y);
                line.setAttribute('class', className);
                svg.appendChild(line);
            };

            // Root to center
            satellites.forEach(id => {
                const satPoint = getCenter(id);
                createLine(centerPoint, satPoint, 'link-dashed');
            });

            // Universe to linked root
            uniKeys.forEach(id => {
                const uniData = entityData[id];
                if(uniData.linked_root) {
                    const uniPoint = getCenter(id);
                    const rootPoint = getCenter(uniData.linked_root);
                    if(rootPoint) {
                        createLine(rootPoint, uniPoint, 'prime-link');
                    }
                }
            });
        }

        // Handle Interactions
        const panel = document.getElementById('details-panel');

        function selectEntity(id) {
            // Update lists
            document.querySelectorAll('.entity-item').forEach(i => i.classList.remove('active'));
            const listItem = document.querySelector(`.entity-item[data-id="${id}"]`);
            if(listItem) listItem.classList.add('active');

            // Update nodes
            document.querySelectorAll('.node').forEach(n => n.classList.remove('active'));
            const nodeEl = document.querySelector(`.node[data-id="${id}"]`);
            if(nodeEl) nodeEl.classList.add('active');

            // Update panel
            const data = entityData[id];
            document.getElementById('detail-title').innerText = data.title;
            document.getElementById('detail-type').innerText = data.type;
            document.getElementById('detail-desc').innerText = data.desc;
            document.getElementById('stat-res').innerText = data.score + '/100';

            const connStat = document.getElementById('stat-conn');
            const typeStat = connStat.parentElement.nextElementSibling.querySelector('.stat-value');
            
            if(data.is_root) {
                connStat.innerText = 'Core Network';
                typeStat.innerText = 'Root Entity';
                typeStat.style.color = 'var(--gold-primary)';
            } else {
                connStat.innerText = data.linked_root ? 'Linked to ' + entityData[data.linked_root].title : 'Unlinked';
                typeStat.innerText = 'Universe';
                typeStat.style.color = 'var(--cyan-accent)';
            }

            panel.style.display = 'block';
            
            // Re-trigger animation
            panel.style.animation = 'none';
            panel.offsetHeight; // Trigger reflow
            panel.style.animation = 'fadeIn 0.4s ease';
        }

        // Init
        window.addEventListener('resize', drawLines);
        // Small delay to ensure layout is done
        setTimeout(buildUI, 100);
        setTimeout(() => {
            const keys = Object.keys(entityData);
            if(keys.length > 0) selectEntity(keys[0]);
        }, 200);

    </script>
</body>
</html>
"""

def generate_entity_dashboard():
    session = get_session()
    try:
        from app.database.models import RootEntity, Universe, RootEntityLink
        
        root_entities = session.query(RootEntity).all()
        
        entity_data = {}
        for r in root_entities:
            entity_data[f"root_{r.id}"] = {
                "id": str(r.id),
                "is_root": True,
                "title": r.name,
                "type": r.type or "Root Entity",
                "desc": r.description or "No description available.",
                "score": r.importance_score
            }
            
        universes = session.query(Universe).all()
        links = session.query(RootEntityLink).filter_by(entity_type="universe").all()
        link_map = {link.entity_id: link.root_entity_id for link in links}
        
        for u in universes:
            linked_root = link_map.get(u.id)
            entity_data[f"uni_{u.id}"] = {
                "id": str(u.id),
                "is_root": False,
                "title": u.name,
                "type": "Universe",
                "desc": u.description or "No description.",
                "score": u.importance_score,
                "linked_root": f"root_{linked_root}" if linked_root else None
            }
            
        json_data = json.dumps(entity_data)
        final_html = HTML_TEMPLATE.replace("{ENTITY_DATA_JSON}", json_data)
        
        # Path to the entity_dashboard.html
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        html_path = os.path.join(base_dir, "entity_dashboard.html")
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(final_html)
            
        print(f"[ZenAI] Dynamically updated HTML dashboard at {html_path}")
    except Exception as e:
        print(f"[ZenAI] Failed to generate dashboard HTML: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    generate_entity_dashboard()
