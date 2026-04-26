# 🎬 Live Demo Dashboard

## Overview

This is a **standalone demo dashboard** with hardcoded/simulated data that shows live botnet detection in action. Perfect for presentations, demos, or showcasing the system without needing the full backend infrastructure.

## Features

✨ **Fully Self-Contained**
- No backend required
- No database needed
- No Kafka or dependencies
- Just open in a browser!

🔴 **Live Simulation**
- Numbers constantly changing
- New flows appearing every 0.8 seconds
- Real-time alerts
- Animated statistics

📊 **What It Shows**
- Total flows analyzed (constantly increasing)
- Benign vs Botnet traffic counts
- Suspicious hosts counter
- Detection rate percentage
- Live flow stream with IP addresses
- Security alerts panel

🎨 **Beautiful Design**
- Gradient purple background
- Glass-morphism effects
- Smooth animations
- Responsive layout
- Hover effects

## How to Use

### Option 1: Direct Open
Simply double-click `demo_dashboard.html` and it will open in your default browser.

### Option 2: From Command Line
```bash
# Windows
start demo_dashboard.html

# Mac
open demo_dashboard.html

# Linux
xdg-open demo_dashboard.html
```

### Option 3: With Python Server
```bash
python -m http.server 8888
# Then open: http://localhost:8888/demo_dashboard.html
```

## What You'll See

### Statistics Cards (Top)
- **Total Flows Analyzed** - Increases continuously
- **Benign Traffic** - Green counter for safe traffic
- **Botnet Detected** - Red counter for malicious traffic
- **Suspicious Hosts** - Number of flagged IP addresses
- **Detection Rate** - Percentage of botnet traffic
- **Active Alerts** - Current security warnings

### Live Flow Stream (Middle)
- Real-time list of network flows
- Shows: Source IP → Destination IP [Protocol]
- Color-coded: Green border = Benign, Red border = Botnet
- Scrollable list (keeps last 15 flows)

### Security Alerts (Bottom)
- Red alert panel
- Shows high-risk botnet detections
- Includes IP address and confidence percentage
- Animated pulse effect on new alerts

## Simulation Details

### Data Generation
- **New flow every 0.8 seconds**
- **35% chance** of botnet detection (realistic ratio)
- **30% chance** of alert when botnet detected
- Uses realistic IP addresses and ports

### IP Addresses Used
- Local IPs: `192.168.1.100`, `10.0.2.15`, `172.16.0.50`
- External IPs: `66.61.90.112`, `125.167.3.52`, `76.169.10.92`
- Service IPs: `74.125.23.139` (Google), `183.57.48.18`

### Protocols
- TCP (most common)
- UDP
- ICMP

### Ports
- Common ports: 80 (HTTP), 443 (HTTPS), 22 (SSH), 53 (DNS)
- Database ports: 3306 (MySQL), 5432 (PostgreSQL), 27017 (MongoDB)

## Customization

### Change Update Speed
Edit line 344 in the HTML:
```javascript
}, 800); // Change 800 to desired milliseconds
```

### Change Botnet Detection Rate
Edit line 267:
```javascript
const isBotnet = Math.random() < 0.35; // Change 0.35 to desired percentage
```

### Change Alert Frequency
Edit line 295:
```javascript
if (isBotnet && Math.random() < 0.3) { // Change 0.3 to desired percentage
```

### Add More IPs
Edit lines 258-262:
```javascript
const ips = [
    '192.168.1.100', '10.0.2.15', // Add your IPs here
];
```

## Use Cases

✅ **Presentations** - Show live detection without setup  
✅ **Demos** - Impress clients or stakeholders  
✅ **Testing UI** - Preview dashboard design  
✅ **Training** - Teach botnet detection concepts  
✅ **Screenshots** - Capture active system for documentation  

## Comparison with Real Dashboard

| Feature | Demo Dashboard | Real Dashboard |
|---------|---------------|----------------|
| Setup Required | ❌ None | ✅ Kafka, Backend, DB |
| Data Source | 🎭 Simulated | 🔬 Real PCAP Analysis |
| ML Predictions | ❌ Random | ✅ Trained Models |
| Dependencies | ❌ None | ✅ Python, Node, Docker |
| Use Case | 🎬 Demos/Presentations | 🔍 Actual Detection |
| Accuracy | 🎲 Simulated | 🎯 Real ML Results |

## Tips for Best Demo

1. **Full Screen** - Press F11 for immersive experience
2. **Let it Run** - Wait 30 seconds for data to accumulate
3. **Point Out Features** - Highlight the live updates
4. **Explain Colors** - Green = Safe, Red = Threat
5. **Show Alerts** - Wait for red alerts to appear

## Technical Details

- **Pure HTML/CSS/JavaScript** - No frameworks
- **No external dependencies** - Everything inline
- **Responsive design** - Works on any screen size
- **Smooth animations** - CSS keyframes
- **Auto-scrolling** - Latest flows always visible

## Browser Compatibility

✅ Chrome/Edge (Recommended)  
✅ Firefox  
✅ Safari  
✅ Opera  
⚠️ IE11 (Limited support)  

## File Size

- **Single file**: ~12 KB
- **No images or external resources**
- **Loads instantly**

---

**Perfect for showcasing your botnet detection system without the complexity of running the full stack!** 🚀
