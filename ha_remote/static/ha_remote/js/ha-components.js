// static/js/ha-components.js

// Import basic Home Assistant components
import 'https://unpkg.com/@polymer/paper-toggle-button@3.0.1/paper-toggle-button.js';
import 'https://unpkg.com/@polymer/paper-slider@3.0.1/paper-slider.js';

// Function to create a Home Assistant entity card
export function createEntityCard(entityId, state, hass) {
  // Create a wrapper element
  const card = document.createElement('div');
  card.className = 'ha-card';
  
  // Create the header
  const header = document.createElement('div');
  header.className = 'card-header';
  header.textContent = state.attributes.friendly_name || entityId;
  card.appendChild(header);
  
  // Create content section
  const content = document.createElement('div');
  content.className = 'card-content';
  
  // Create appropriate controls based on entity type
  if (entityId.startsWith('light.')) {
    // Create a toggle button for lights
    const row = document.createElement('div');
    row.className = 'ha-entity-toggle';
    
    const toggle = document.createElement('paper-toggle-button');
    toggle.checked = state.state === 'on';
    toggle.addEventListener('change', () => {
      const service = toggle.checked ? 'turn_on' : 'turn_off';
      hass.callService('light', service, { entity_id: entityId });
    });
    
    row.appendChild(toggle);
    content.appendChild(row);
    
    // Add brightness slider if the light supports it
    if (state.attributes.brightness !== undefined) {
      const brightnessRow = document.createElement('div');
      brightnessRow.className = 'ha-brightness-slider';
      
      const label = document.createElement('div');
      label.className = 'slider-label';
      label.textContent = 'Brightness';
      brightnessRow.appendChild(label);
      
      const slider = document.createElement('paper-slider');
      slider.min = 0;
      slider.max = 255;
      slider.value = state.attributes.brightness || 0;
      slider.disabled = state.state !== 'on';
      slider.addEventListener('change', () => {
        hass.callService('light', 'turn_on', {
          entity_id: entityId,
          brightness: slider.value
        });
      });
      
      brightnessRow.appendChild(slider);
      content.appendChild(brightnessRow);
    }
  } else if (entityId.startsWith('switch.')) {
    // Create toggle for switches
    const row = document.createElement('div');
    row.className = 'ha-entity-toggle';
    
    const toggle = document.createElement('paper-toggle-button');
    toggle.checked = state.state === 'on';
    toggle.addEventListener('change', () => {
        const service = toggle.checked ? 'turn_on' : 'turn_off';
        hass.callService('switch', service, { entity_id: entityId });
      });
      
      row.appendChild(toggle);
      content.appendChild(row);
    } else if (entityId.startsWith('climate.')) {
      // Create climate controls
      const row = document.createElement('div');
      row.className = 'ha-climate-controls';
      
      // Temperature display
      const temp = document.createElement('div');
      temp.className = 'current-temp';
      temp.textContent = `${state.attributes.current_temperature}°${state.attributes.temperature_unit}`;
      row.appendChild(temp);
      
      // Mode selector
      if (state.attributes.hvac_modes) {
        const modeSelect = document.createElement('select');
        modeSelect.className = 'mode-select';
        
        state.attributes.hvac_modes.forEach(mode => {
          const option = document.createElement('option');
          option.value = mode;
          option.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
          option.selected = mode === state.state;
          modeSelect.appendChild(option);
        });
        
        modeSelect.addEventListener('change', () => {
          hass.callService('climate', 'set_hvac_mode', {
            entity_id: entityId,
            hvac_mode: modeSelect.value
          });
        });
        
        const modeLabel = document.createElement('div');
        modeLabel.className = 'control-label';
        modeLabel.textContent = 'Mode: ';
        modeLabel.appendChild(modeSelect);
        row.appendChild(modeLabel);
      }
      
      content.appendChild(row);
      
      // Temperature controls
      if (state.attributes.min_temp !== undefined && state.attributes.max_temp !== undefined) {
        const tempRow = document.createElement('div');
        tempRow.className = 'temperature-controls';
        
        const tempSlider = document.createElement('paper-slider');
        tempSlider.min = state.attributes.min_temp;
        tempSlider.max = state.attributes.max_temp;
        tempSlider.step = 0.5;
        tempSlider.value = state.attributes.temperature || state.attributes.current_temperature;
        tempSlider.disabled = state.state === 'off';
        tempSlider.addEventListener('change', () => {
          hass.callService('climate', 'set_temperature', {
            entity_id: entityId,
            temperature: tempSlider.value
          });
        });
        
        const sliderLabel = document.createElement('div');
        sliderLabel.className = 'slider-label';
        sliderLabel.textContent = 'Target: ';
        tempRow.appendChild(sliderLabel);
        tempRow.appendChild(tempSlider);
        
        content.appendChild(tempRow);
      }
    } else {
      // Generic state display for other entities
      const stateRow = document.createElement('div');
      stateRow.className = 'entity-state';
      stateRow.textContent = state.state;
      content.appendChild(stateRow);
    }
    
    card.appendChild(content);
    return card;
  }