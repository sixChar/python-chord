
// How many times do we see a node having a predecessor before saying it is no longer recent
const RECENT_THRESHOLD = 3;

// State of the network
const state = {
    nodes:[],
    highlighted: new Map(),
    recentlyAdded: new Map(),
}


const resizeCanvas = function() {
    const canvas = document.getElementById('main-canvas');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    draw();
}

const draw = function() {
    const canvas = document.getElementById('main-canvas');
    const ctx = canvas.getContext('2d');

    //clear transform
    // center and then scale
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    const scale = Math.min(canvas.height, canvas.width) / 3;
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.scale(scale, scale);

    // Draw circle
    
    circleX = 0;
    circleY = 0;
    ctx.beginPath()
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 0.005;
    ctx.stroke();
    

    // For drawing nodes
    ctx.fillStyle = 'white';
    const nodeWidth = 0.05;
    const nodeHeight = 0.05;
    
    // For writing port numbers next to nodes.
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '0.5em monospace';
    
    
    let nodeX, nodeY, angle, nodeLoc, locStr;
    for (let i=0; i < state.nodes.length; i++) {
        angle = 2 * Math.PI * (i / state.nodes.length) - Math.PI/ 2;
        nodeX = Math.cos(angle) + circleX;
        nodeY = Math.sin(angle) + circleY;
        state.nodes[i].nodeX = nodeX;
        state.nodes[i].nodeY = nodeY;
        state.nodes[i].angle = angle;
    }

    for (let i=0; i < state.nodes.length; i++) {
        let node = state.nodes[i];
        let succ_loc = node.successors[0];
        let succ = null;
        for (let j = 0; j < state.nodes.length; j++) {
            let loc = state.nodes[j].loc;
            if (loc && succ_loc && loc[0] == succ_loc[0] && loc[1] == succ_loc[1]) {
                succ = state.nodes[j];
                state.nodes[j].isSuccessor = true;
                break
            }
        }
        if (succ) {
            ctx.beginPath();
            ctx.moveTo(node.nodeX, node.nodeY);
            ctx.lineTo(succ.nodeX, succ.nodeY);
            ctx.stroke();
        }
    }


    /*
    let recentCount, recentStr;
    // Typically the last node added will be the one highlighted and that will be the last more often than the first. Hence looping from the last to first.
    for (let i=state.nodes.length - 1; i >= 0; i--) {
        nodeLoc = state.nodes[i].loc;
        nodeX = state.nodes[i].nodeX;
        nodeY = state.nodes[i].nodeY;
        if (state.highlighted && state.highlighted[0] == nodeLoc[0] && state.highlighted[1] == nodeLoc[1]) {
            ctx.fillStyle = 'lightgreen'; 
            ctx.fillRect(nodeX - nodeWidth/2, nodeY-nodeHeight/2, nodeWidth, nodeHeight);

        } else if (!state.nodes[i].isSuccessor) {
            ctx.fillStyle = 'gray'; 
            ctx.fillRect(nodeX - nodeWidth/2, nodeY-nodeHeight/2, nodeWidth, nodeHeight);
        } else if (state.recentlyAdded.has(nodeLoc[0] + ':' + nodeLoc[1])) {
            recentStr = nodeLoc[0] + ':' + nodeLoc[1];
            recentCount = state.recentlyAdded.get(recentStr);
            ctx.fillStyle = 'yellow'
            ctx.fillRect(nodeX - nodeWidth/2, nodeY-nodeHeight/2, nodeWidth, nodeHeight);
            if (recentCount <= 0) {
                state.recentlyAdded.delete(recentStr);
            }
            else {
                state.recentlyAdded.set(recentStr, recentCount - 1);
            }

        } else {
            ctx.fillStyle = 'white';
            ctx.fillRect(nodeX - nodeWidth/2, nodeY-nodeHeight/2, nodeWidth, nodeHeight);
        }

        ctx.fillStyle = 'white';
        locStr = nodeLoc[1];
        ctx.scale(1/scale, 1/scale);
        ctx.fillText(locStr, nodeX * scale * 1.1, nodeY * scale * 1.075);
        ctx.scale(scale, scale);
    }
    */
    

    ctx.restore();
    drawNodes();
}


const drawNodes = function() {
    const container = document.getElementById('node-container');
    const newContainer = document.createElement('div');

    const width = window.innerWidth;
    const height = window.innerHeight;
    const radius = 2 * Math.min(width,height) / 3 / 2;
    
    const nodeSize = Math.floor(0.025 * Math.min(width, height));
    const labelWidth = Math.floor(0.025 * Math.min(width, height));
    
    newContainer.id = 'node-container';
    newContainer.className = 'node-container';

    for (let i=0; i < state.nodes.length; i++) {
        const node = state.nodes[i];
        const leftOff = node.nodeX * radius;
        const topOff = node.nodeY * radius;
        const nodeLeft = Math.floor(leftOff + width / 2 - nodeSize/2);
        const nodeTop = Math.floor(topOff + height / 2 - nodeSize/2);
        const labelLeft = Math.floor(1.15 * leftOff + width/2 - labelWidth/2);
        const labelTop = Math.floor(1.15 * topOff + height/2);

        const nodeElem = document.createElement('div');
        nodeElem.className = 'node-elem';
        nodeElem.style.setProperty('left', nodeLeft + 'px');
        nodeElem.style.setProperty('top', nodeTop + 'px');
        nodeElem.style.setProperty('width', nodeSize + 'px');
        nodeElem.style.setProperty('height', nodeSize + 'px');
        let nodeColor = 'white';
        if (!node.isSuccessor) {
            nodeColor =  'gray';
        }
        const locStr = node.loc[0] + ':' + node.loc[1];

        const recentCount = state.recentlyAdded.get(locStr); 
        if (state.highlighted.has(locStr)) {
            nodeColor = 'lightgreen';
        }
        if (!recentCount || recentCount <= 0) {
            state.recentlyAdded.delete(locStr);
        }
        else {
            nodeElem.style.setProperty('border', '5px solid yellow');
            if (node.isSuccessor) {
                state.recentlyAdded.set(locStr, recentCount - 1);
            }
        }

        nodeElem.onclick = (e) => {
            if (state.highlighted.has(locStr)) {
                state.highlighted.delete(locStr);
                nodeElem.style.setProperty('background', nodeColor);
            }
            else {
                state.highlighted.set(locStr, 1);
                nodeElem.style.setProperty('background', 'lightgreen');
            }
        };
        nodeElem.style.setProperty('background', nodeColor);

        const nodeLabel = document.createElement('div');
        nodeLabel.textContent = node.loc[1];
        nodeLabel.className = 'node-label';
        nodeLabel.style.setProperty('position', 'absolute');
        nodeLabel.style.setProperty('left', labelLeft + 'px');
        nodeLabel.style.setProperty('top', labelTop + 'px');
        nodeLabel.style.setProperty('width', labelWidth + 'px');


        newContainer.appendChild(nodeElem);
        newContainer.appendChild(nodeLabel);
    }

    container.parentNode.replaceChild(newContainer, container);
}



const addNode = async function(e) {
    const data = await fetch('/add');
    const jsn = await data.json();
    console.log(jsn);
    state.recentlyAdded.set(jsn.node[0] + ':' + jsn.node[1], RECENT_THRESHOLD);
    nodeInfo();    
}


const removeNode = async function(e) {
    const data = await fetch('/remove')
    const jsn = await data.json()
    console.log(jsn);
    if (jsn.node) {
        state.recentlyAdded.delete(jsn.node[0] + ':' + jsn.node[1]);
    }
    nodeInfo();
}


const nodeInfo = async function(e) {
    const resp = await fetch('/node-info');
    const json_nodes = (await resp.json());
    const nodes = json_nodes.nodes;

    
    
    let matched, temp;

    // First node is always either some node's successor or it's own successor
    if (nodes.length > 0) {
        nodes[0].isSuccessor = true;
    }
    for (let i=0; i < nodes.length; i++) {
        succ_loc = nodes[i].successors[0];
        for (let j=i+1; j < nodes.length; j++) {
            loc = nodes[j].loc;
            if (succ_loc[0] == loc[0] && succ_loc[1] == loc[1]) {
                temp = nodes[i+1];
                nodes[i+1] = nodes[j];
                nodes[j] = temp;
                break
            }
        }
    }
    
    if (true) {
        state.nodes = nodes;
        draw();
    }
}


window.onload = function() {
    const canvas = document.getElementById('main-canvas');
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const addNodeBtn = document.getElementById('add-node-btn');
    addNodeBtn.onclick = addNode;

    const removeNodeBtn = document.getElementById('remove-node-btn');
    removeNodeBtn.onclick = removeNode;

    const infoBtn = document.getElementById('info-btn');
    infoBtn.onclick = () => nodeInfo();

    setInterval(() => {document.hasFocus() && nodeInfo()}, 1000);
}



