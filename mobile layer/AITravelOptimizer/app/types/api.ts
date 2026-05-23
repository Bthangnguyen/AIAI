// Data Contracts bridging Layer 2 (LLM) -> Layer 3 (DB) -> Layer 4 (Solver)

export interface TimeWindowSpec {
  start_min: number;
  end_min: number;
}

export interface LLMDataContract {
  destination?: string;
  budget_max?: number;
  radius_km?: number;
  num_days: number;
  time_window?: TimeWindowSpec;
  tags: string[];
  locked_pois: string[];
  weather_preference?: string;
  hotel_lat?: number;
  hotel_lon?: number;
  hotel_name?: string;

  // Scheduling hints
  estimated_pois?: number;
  time_slot?: string;
  trip_duration_hours?: number;
  vibe?: string;
  trip_type?: string;

  // Preferences
  preferred_pace?: 'chill' | 'balanced' | 'intense';
  walking_tolerance?: 'low' | 'medium' | 'high';
  food_preferences?: string[];
  avoid_tags?: string[];
  
  target_category_distribution?: Record<string, number>;
}

export interface POIScoreBreakdown {
  semantic_score: number;
  quality_score: number;
  localness_score: number;
  novelty_score: number;
  comfort_score: number;
  budget_score: number;
  distance_score: number;
  diversity_gain: number;
}

export interface POIResponse {
  uuid: string;
  name: string;
  category: string;
  description?: string;
  latitude: number;
  longitude: number;
  visit_duration_min: number;
  price: number;
  entrance_fee: number;
  open_time: number;
  close_time: number;
  priority_score: number;
  tags?: string[];
  is_locked: boolean;
  score_breakdown?: POIScoreBreakdown;
  utility_score: number;
}

// SSE Event Types
export type SSEStage = 
  | 'idle'
  | 'intent_extraction_started'
  | 'intent_extraction_completed'
  | 'poi_search_started'
  | 'poi_search_completed'
  | 'optimization_started'
  | 'optimization_completed'
  | 'validation_completed'
  | 'narrative_completed'
  | 'completed'
  | 'error';
