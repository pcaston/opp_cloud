// ha_remote/static/ha_remote/js/ha-connection.js

// This script connects to your Django WebSocket and bridges to Home Assistant frontend
function initHaConnection(wsUrl, siteInfo) {
  let socket;
  let connectionAttempts = 0;
  let authenticated = false;
  
  // Connect to WebSocket
  function connect() {
      socket = new WebSocket(wsUrl);
      
      socket.onopen = () => {
          console.log('WebSocket connected');
          // Authenticate with your backend
          authenticate();
      };
      
      socket.onclose = () => {
          console.log('WebSocket disconnected');
          authenticated = false;
          
          // Reconnect logic
          if (connectionAttempts < 5) {
              connectionAttempts++;
              setTimeout(connect, 1000 * connectionAttempts);
          }
      };
      
      socket.onmessage = (event) => {
          const message = JSON.parse(event.data);
          
          // Handle authentication response
          if (message.type === 'auth_success') {
              authenticated = true;
              connectionAttempts = 0;
              console.log('Authentication successful');
              
              // Initialize Home Assistant frontend
              initHomeAssistant();
          }
          
          // Forward messages to Home Assistant frontend
          forwardMessageToHass(message);
      };
  }
  
  // Authenticate with your WebSocket backend
  function authenticate() {
      // Get user credentials - you need to implement this
      // based on how authentication works in your app
      const token = getAuthToken(); // Implement this function
      
      socket.send(JSON.stringify({
          type: 'authenticate',
          email: getUserEmail(), // Implement this function
          password: getUserPassword(), // Implement this function 
          site_name: siteInfo.site_name
      }));
  }
  
  // Initialize Home Assistant frontend
  function initHomeAssistant() {
      // Get the Home Assistant element
      const homeAssistant = document.querySelector('home-assistant');
      
      // Set up options for Home Assistant
      const hassOptions = {
          // Configure the Home Assistant frontend to use your connection
          // instead of its default connection logic
          async callService(domain, service, serviceData) {
              return sendHassCommand({
                  type: 'call_service',
                  domain,
                  service,
                  service_data: serviceData
              });
          },
          async getStates() {
              return sendHassCommand({
                  type: 'get_states'
              });
          },
          async getConfig() {
              return sendHassCommand({
                  type: 'get_config'
              });
          }
          // Add other methods as needed
      };
      
      // Set options on Home Assistant element
      homeAssistant.setOptions(hassOptions);
  }
  
  // Send a command to Home Assistant via your WebSocket
  async function sendHassCommand(command) {
      return new Promise((resolve, reject) => {
          if (!socket || socket.readyState !== WebSocket.OPEN || !authenticated) {
              reject(new Error('Not connected'));
              return;
          }
          
          // Add an ID to track the response
          const id = Date.now();
          command.id = id;
          
          // Set up a response handler
          const responseHandler = (event) => {
              const message = JSON.parse(event.data);
              if (message.type === 'result' && message.id === id) {
                  // Remove the one-time handler
                  socket.removeEventListener('message', responseHandler);
                  
                  if (message.success) {
                      resolve(message.result);
                  } else {
                      reject(new Error(message.error?.message || 'Command failed'));
                  }
              }
          };
          
          // Add the response handler
          socket.addEventListener('message', responseHandler);
          
          // Send the command
          socket.send(JSON.stringify(command));
          
          // Set a timeout
          setTimeout(() => {
              socket.removeEventListener('message', responseHandler);
              reject(new Error('Command timed out'));
          }, 10000);
      });
  }
  
  // Forward messages from your backend to Home Assistant frontend
  function forwardMessageToHass(message) {
      // Get the Home Assistant element
      const homeAssistant = document.querySelector('home-assistant');
      if (!homeAssistant) return;
      
      // Process different message types
      if (message.type === 'event' && message.event?.event_type === 'state_changed') {
          // Update Home Assistant state
          homeAssistant.updateState(message.event.data);
      }
      // Handle other message types as needed
  }
  
  // Start the connection
  connect();
}