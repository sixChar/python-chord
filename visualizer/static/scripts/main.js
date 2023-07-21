
// How many times do we see a node having a predecessor before saying it is no longer recent
const RECENT_THRESHOLD = 5;

// State of the network
const state = {
    nodes:[],
    highlighted: null,
    recentlyAdded: new Map(),
}
fetch('/node-count').then(data => data.text()).then(text => state.nodes.length = text)

const resizeCanvas = function() {
    const canvas = document.getElementById('main-canvas');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    drawCanvas();
}

const drawCanvas = function() {
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
    
    circleRadius = 1;
    circleX = 0;
    circleY = 0;
    ctx.beginPath()
    //ctx.arc(circleX, circleY, circleRadius, 0, 2*Math.PI);
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
        nodeX = circleRadius * Math.cos(angle) + circleX;
        nodeY = circleRadius * Math.sin(angle) + circleY;
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
    

    ctx.restore();
}


const addNode = function(e) {
    fetch('/add').then(data => data.json()).then(jsn => {
        console.log(jsn);
        state.recentlyAdded.set(jsn.node[0] + ':' + jsn.node[1], RECENT_THRESHOLD);
    })
    drawCanvas();
}


const removeNode = function(e) {
    fetch('/remove').then(data => data.json()).then(jsn => {
        console.log(jsn);
        if (jsn.node) {
            state.recentlyAdded.delete(jsn.node[0] + ':' + jsn.node[1]);
        }
    });
    drawCanvas();
}


const nodeInfo = async function(e) {
    const resp = await fetch('/node-info');
    const json_nodes = (await resp.json());
    const nodes = json_nodes.nodes;

    
    
    let matched, temp;

    // First node is always either some node's successor or it's on successor
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
    
    
    state.nodes = nodes;
    drawCanvas();
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



