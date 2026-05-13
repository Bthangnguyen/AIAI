import React from 'react';
import './Timeline.css';

function Timeline({ routes }) {
  const timeInfo = React.useMemo(() => {
    if (!routes || routes.length === 0) {
      return { minTime: 0, maxTime: 0, duration: 0 };
    }

    let minTime = Infinity;
    let maxTime = -Infinity;

    routes.forEach(routeData => {
      const stops = routeData.route || [];
      if (stops.length === 0) return;
      
      stops.forEach(stop => {
        // Support both formats: arrival_time (Gurobi) and time (OR-Tools)
        const arrivalMin = stop.arrival_time || stop.time || 0;
        const isDepot = stop.location === 0 || stop.demand === 0;
        
        // Calculate service time from demand or load_before/load_after
        let serviceMin = 0;
        if (!isDepot) {
          if (stop.demand !== undefined) {
            // Gurobi format
            serviceMin = 10 + (2 * stop.demand);
          } else if (stop.load_before !== undefined && stop.load_after !== undefined) {
            // OR-Tools format
            const units = stop.load_before - stop.load_after;
            serviceMin = 10 + (2 * units);
          }
        }
        
        const departureMin = arrivalMin + serviceMin;
        
        minTime = Math.min(minTime, arrivalMin);
        maxTime = Math.max(maxTime, departureMin);
      });
    });

    if (minTime === Infinity || maxTime === -Infinity) {
      return { minTime: 0, maxTime: 0, duration: 0 };
    }

    minTime = Math.floor(minTime / 60) * 60;
    maxTime = Math.ceil(maxTime / 60) * 60;

    return { minTime, maxTime, duration: maxTime - minTime };
  }, [routes]);

  // Generate time markers for the x-axis
  const timeMarkers = React.useMemo(() => {
    if (timeInfo.duration === 0) return [];
    
    const markers = [];
    const numMarkers = 8; // Show 8 time markers
    
    for (let i = 0; i <= numMarkers; i++) {
      const minutes = timeInfo.minTime + (timeInfo.duration * i / numMarkers);
      const hours = Math.floor(minutes / 60);
      const mins = Math.floor(minutes % 60);
      markers.push({
        position: (i / numMarkers) * 100,
        label: `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`
      });
    }
    
    return markers;
  }, [timeInfo]);

  if (!routes || routes.length === 0 || timeInfo.duration === 0) {
    return (
      <div className="timeline">
        <p>Timeline data not available.</p>
      </div>
    );
  }

  return (
    <div className="timeline">
      <h3>Timeline</h3>
      
      {/* Time axis */}
      <div className="time-axis">
        {timeMarkers.map((marker, idx) => (
          <div 
            key={idx} 
            className="time-marker"
            style={{ left: `${marker.position}%` }}
          >
            <div className="marker-line"></div>
            <div className="marker-label">{marker.label}</div>
          </div>
        ))}
      </div>
      
      <div className="timeline-content">
        {routes.map((routeData, routeIdx) => {
          const stops = routeData.route || [];
          
          return (
            <div key={routeIdx} className="vehicle-timeline-row">
              <div className="vehicle-header">
                <strong>Vehicle {routeData.vehicle_id + 1}</strong>
                <span className="vehicle-stats">
                  {routeData.num_customers} stops • {routeData.distance_formatted}
                </span>
              </div>
              
              <div className="timeline-bar-container">
                {stops.map((stop, stopIdx) => {
                  const isDepot = stop.location === 0 || stop.demand === 0;
                  
                  // Support both formats: arrival_time (Gurobi) and time (OR-Tools)
                  const arrivalMin = stop.arrival_time || stop.time || 0;
                  
                  // Calculate service time from demand or load_before/load_after
                  let serviceMin = 0;
                  if (!isDepot) {
                    if (stop.demand !== undefined) {
                      // Gurobi format
                      serviceMin = 10 + (2 * stop.demand);
                    } else if (stop.load_before !== undefined && stop.load_after !== undefined) {
                      // OR-Tools format
                      const units = stop.load_before - stop.load_after;
                      serviceMin = 10 + (2 * units);
                    }
                  }
                  
                  let travelMin = 0;
                  let travelKm = 0;
                  if (stopIdx > 0) {
                    const prevStop = stops[stopIdx - 1];
                    const prevIsDepot = prevStop.location === 0 || prevStop.demand === 0;
                    const prevArrivalMin = prevStop.arrival_time || prevStop.time || 0;
                    
                    // Calculate previous service time
                    let prevServiceMin = 0;
                    if (!prevIsDepot) {
                      if (prevStop.demand !== undefined) {
                        prevServiceMin = 10 + (2 * prevStop.demand);
                      } else if (prevStop.load_before !== undefined && prevStop.load_after !== undefined) {
                        const prevunits = prevStop.load_before - prevStop.load_after;
                        prevServiceMin = 10 + (2 * prevunits);
                      }
                    }
                    
                    const prevDepartureMin = prevArrivalMin + prevServiceMin;
                    travelMin = arrivalMin - prevDepartureMin;
                    travelKm = stop.segment_distance || 0;
                  }
                  
                  // Skip first depot (departure point) - we only show travel segments from it
                  if (isDepot && stopIdx === 0) return null;
                  
                  // If this is the return to depot (last stop), only show travel segment
                  if (isDepot && stopIdx === stops.length - 1) {
                    const travelStartPercent = ((arrivalMin - travelMin - timeInfo.minTime) / timeInfo.duration) * 100;
                    const travelWidthPercent = (travelMin / timeInfo.duration) * 100;
                    
                    return (
                      <div
                        key={stopIdx}
                        className="timeline-segment travel"
                        style={{
                          left: `${travelStartPercent}%`,
                          width: `${travelWidthPercent}%`
                        }}
                        title="Return to Depot"
                      >
                        <div className="segment-info">
                          <span>{travelKm.toFixed(1)} km</span>
                          <span>{Math.round(travelMin)} min</span>
                          <span>→ Deposito</span>
                        </div>
                      </div>
                    );
                  }
                  
                  const travelStartPercent = stopIdx > 0 
                    ? ((arrivalMin - travelMin - timeInfo.minTime) / timeInfo.duration) * 100
                    : 0;
                  const travelWidthPercent = (travelMin / timeInfo.duration) * 100;
                  const serviceStartPercent = ((arrivalMin - timeInfo.minTime) / timeInfo.duration) * 100;
                  const serviceWidthPercent = (serviceMin / timeInfo.duration) * 100;
                  
                  return (
                    <React.Fragment key={stopIdx}>
                      {travelMin > 0 && (
                        <div
                          className="timeline-segment travel"
                          style={{
                            left: `${travelStartPercent}%`,
                            width: `${travelWidthPercent}%`
                          }}
                          title={`Travel to Customer ${stop.location}`}
                        >
                          <div className="segment-info">
                            <span>{travelKm.toFixed(1)} km</span>
                            <span>{Math.round(travelMin)} min</span>
                            <span>→ Cliente {stop.location}</span>
                          </div>
                        </div>
                      )}
                      
                      <div
                        className="timeline-segment service"
                        style={{
                          left: `${serviceStartPercent}%`,
                          width: `${serviceWidthPercent}%`
                        }}
                        title={`Service at Customer ${stop.location}`}
                      >
                        <div className="segment-info">
                          <span>{serviceMin} min scarico</span>
                          <span>Cliente {stop.location}</span>
                        </div>
                      </div>
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default Timeline;
