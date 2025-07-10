import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// LetzAI Generator Extension
app.registerExtension({
    name: "letzai.generator",
    async setup() {
        // Status message handler
        function statusMessageHandler(event) {
            const message = event.detail.message;
            
            // Find all LetzAI Generator nodes
            const letzaiNodes = app.graph.getNodesByType("LetzAI Generator");
            
            letzaiNodes.forEach(node => {
                // Update node badge/status
                if (node.badge) {
                    node.badge.text = message;
                } else {
                    node.badge = { text: message };
                }
                
                // Update node color based on status
                if (message.includes("completed")) {
                    node.bgcolor = "#2d5a2d"; // Green background for success
                    node.title = "LetzAI Generator ✅";
                } else if (message.includes("cancelled")) {
                    node.bgcolor = "#5a4a2d"; // Orange background for cancelled
                    node.title = "LetzAI Generator 🛑";
                } else if (message.includes("failed") || message.includes("error")) {
                    node.bgcolor = "#5a2d2d"; // Red background for error
                    node.title = "LetzAI Generator ❌";
                } else if (message.includes("Status:")) {
                    node.bgcolor = "#2d4a5a"; // Blue background for in progress
                    node.title = "LetzAI Generator 🔄";
                } else {
                    node.bgcolor = "#3a3a3a"; // Default background
                    node.title = "LetzAI Generator";
                }
            });
            
            // Force a redraw
            app.graph.setDirtyCanvas(true);
            
            // Also show in console for debugging
            console.log("LetzAI Status:", message);
        }
        
        // Error message handler
        function errorMessageHandler(event) {
            const message = event.detail.message;
            
            // Show alert for errors
            alert(`LetzAI Error: ${message}`);
            
            // Update node appearance
            const letzaiNodes = app.graph.getNodesByType("LetzAI Generator");
            letzaiNodes.forEach(node => {
                node.badge = { text: "Error" };
                node.bgcolor = "#5a2d2d"; // Red background for error
                node.title = "LetzAI Generator ❌"; // Update title to show error
            });
            
            app.graph.setDirtyCanvas(true);
            console.error("LetzAI Error:", message);
        }
        
        // Register event listeners
        app.api.addEventListener("letzai.status", statusMessageHandler);
        app.api.addEventListener("letzai.error", errorMessageHandler);
    },
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "LetzAI Generator") {
            // Override the node's onExecuted method to reset appearance
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                // Reset node appearance when execution starts
                this.badge = { text: "Starting..." };
                this.bgcolor = "#3a3a3a";
                this.title = "LetzAI Generator"; // Reset title
                
                if (onExecuted) {
                    onExecuted.apply(this, arguments);
                }
            };
            
            // Add status badge display
            const onDrawForeground = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function(ctx) {
                if (onDrawForeground) {
                    onDrawForeground.apply(this, arguments);
                }
                
                // Draw status badge if it exists
                if (this.badge && this.badge.text) {
                    ctx.save();
                    ctx.font = "10px Arial";
                    ctx.fillStyle = "#ffffff";
                    ctx.textAlign = "center";
                    
                    const badgeWidth = Math.max(120, ctx.measureText(this.badge.text).width + 10);
                    const badgeHeight = 16;
                    const badgeX = this.size[0] / 2 - badgeWidth / 2;
                    const badgeY = -20;
                    
                    // Draw badge background
                    ctx.fillStyle = "#333333";
                    ctx.fillRect(badgeX, badgeY, badgeWidth, badgeHeight);
                    
                    // Draw badge border
                    ctx.strokeStyle = "#555555";
                    ctx.strokeRect(badgeX, badgeY, badgeWidth, badgeHeight);
                    
                    // Draw badge text
                    ctx.fillStyle = "#ffffff";
                    ctx.fillText(this.badge.text, this.size[0] / 2, badgeY + 12);
                    
                    ctx.restore();
                }
            };
        }
    }
}); 