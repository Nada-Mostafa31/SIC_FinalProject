# Final-IoT-Project: PET Care System

## 1. Project Overview

  Smart Pet Care System is an intelligent IoT-based solution designed to help pet owners monitor, understand, and care for their pets — starting with cats, but scalable to all kinds of pets.
The system leverages AI, sound recognition, and computer vision to understand the pet’s needs, ensure its safety, and automate daily caring tasks.



---

## 2. Main Idea
The goal of this project is to create a home-integrated pet assistant that:

- Recognizes the pet’s sounds to understand what it needs (e.g., hungry, thirsty, wants to play, etc.).

- Uses camera vision to detect where the pet is in the home.

- Automates actions to ensure safety and comfort — such as closing windows or doors when the pet is nearby.

- Feeds the pet automatically when hunger is detected and monitors food levels to track its eating behavior.

- Sends alerts and updates to the owner through ThingsBoard dashboards and WhatsApp notifications via Node-RED.

---

## 3. System Architecture

1. **Sensors & Actuators**:
   - Airpods Microphone for sound detection
   - Camera for pet tracking
   - Servo motor for automatic feeding
   - Ultrasonic for detecting the food level
   - Another Servo motor for Door/window for safety automation closing
   - PIR Sensor for detecting the motion of the pet

2. **Processing Unit**:
   - Raspberry Pi 4 running Python scripts
   - AI models for sound and image recognition
  
3. **Communication Layer**:
   - **MQTT protocol** for IoT data transfer
   - HiveMQ broker for communication between devices
  
4. **Cloud Integration**:
   - **ThingsBoard**: Visualization and data storage
   - **Node-RED**: Alert logic and WhatsApp message integration
     
---

## 4. Implementation
For MQTT Integration in Thingsboard : Follow the guide: (https://thingsboard.io/docs/paas/user-guide/integrations/mqtt/)
  
---

## 5. Future Improvements
  
- Expand to support dogs and other pets.
- Add emotion recognition from sound and video.
- Implement mobile app for better control and monitoring.
- Integrate health sensors (temperature, activity tracking, etc.).
- Deploy outdoor version for smart garden pet care.

Here is the Business Model Canvas for the project: 

<img width="2000" height="1414" alt="Business Model Canvas" src="https://github.com/user-attachments/assets/fca324f3-3183-4127-81a0-626c864e8243" />


---
## 6. Team Members
Group: IoT702
1. Basmala Ehab
2. Nada Mostafa
3. Kareem Galal
