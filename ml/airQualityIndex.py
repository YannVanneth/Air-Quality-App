import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import logging
import numpy as np
from datetime import datetime, timedelta
import json
import pickle
import os
from typing import Dict, List, Optional, Tuple, Union

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AirQualityIndex:
    def __init__(self, config: Optional[Dict] = None):
        self.model = None
        self.feature_columns = []
        self.categorical_features = []
        self.is_trained = False
        self.model_metrics = {}
        self.config = {
            'model_params': {
                'iterations': 1000,
                'learning_rate': 0.1,
                'depth': 8,
                'eval_metric': 'RMSE',
                'random_seed': 42,
                'verbose': 100
            },
            'data_params': {
                'test_size': 0.2,
                'random_state': 42
            },
            'feature_engineering': {
                'create_interactions': True,
                'create_time_features': True,
                'normalize_features': False
            }
        }

        if config:
            self._update_config(config)

        self.aqi_breakpoints = {
            'PM2.5': [
                (0, 12.0, 0, 50),
                (12.1, 35.4, 51, 100),
                (35.5, 55.4, 101, 150),
                (55.5, 150.4, 151, 200),
                (150.5, 250.4, 201, 300),
                (250.5, 350.4, 301, 400),
                (350.5, 500.4, 401, 500)
            ],
            'PM10': [
                (0, 54, 0, 50),
                (55, 154, 51, 100),
                (155, 254, 101, 150),
                (255, 354, 151, 200),
                (355, 424, 201, 300),
                (425, 504, 301, 400),
                (505, 604, 401, 500)
            ]
        }
        
        logger.info("AirQualityIndex system initialized")

    def _update_config(self, config: Dict):
        """Update configuration with provided config dictionary"""
        for key, value in config.items():
            if key in self.config and isinstance(self.config[key], dict):
                self.config[key].update(value)
            else:
                self.config[key] = value

    def generate_sample_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """
        Generate synthetic air quality data for training/testing

        Args:
            n_samples: Number of samples to generate

        Returns:
            DataFrame with synthetic air quality data
        """
        logger.info(f"Generating {n_samples} synthetic air quality samples")
        np.random.seed(self.config['model_params']['random_seed'])
        
        data = {
            'timestamp': pd.date_range(start='2020-01-01', periods=n_samples, freq='H'),
            'PM2.5': np.random.normal(25, 12, n_samples),
            'PM10': np.random.normal(45, 20, n_samples),
            'NO2': np.random.normal(20, 8, n_samples),
            'SO2': np.random.normal(15, 6, n_samples),
            'CO': np.random.normal(1.2, 0.5, n_samples),
            'O3': np.random.normal(80, 30, n_samples),
            'temperature': np.random.normal(22, 8, n_samples),
            'humidity': np.random.normal(60, 15, n_samples),
            'wind_speed': np.random.normal(10, 5, n_samples),
            'pressure': np.random.normal(1013, 20, n_samples),
            'location': np.random.choice(['Urban', 'Suburban', 'Rural'], n_samples),
            'season': np.random.choice(['Spring', 'Summer', 'Fall', 'Winter'], n_samples)
        }

        df = pd.DataFrame(data)

        # Clip values to realistic ranges
        df['PM2.5'] = np.clip(df['PM2.5'], 0, 500)
        df['PM10'] = np.clip(df['PM10'], 0, 600)
        df['NO2'] = np.clip(df['NO2'], 0, 200)
        df['SO2'] = np.clip(df['SO2'], 0, 100)
        df['CO'] = np.clip(df['CO'], 0, 50)
        df['O3'] = np.clip(df['O3'], 0, 300)
        df['humidity'] = np.clip(df['humidity'], 0, 100)
        df['wind_speed'] = np.clip(df['wind_speed'], 0, 50)

        # Calculate AQI for each row
        df['AQI'] = df.apply(self._calculate_aqi_row, axis=1)

        logger.info("Sample data generated successfully")
        return df

    def _calculate_aqi_row(self, row: pd.Series) -> float:
        """Calculate AQI for a single row of data"""
        pm25_aqi = self._calculate_pollutant_aqi(row['PM2.5'], 'PM2.5')
        pm10_aqi = self._calculate_pollutant_aqi(row['PM10'], 'PM10')

        base_aqi = max(pm25_aqi, pm10_aqi)

        # Weather effects
        weather_effect = (row['temperature'] * 0.5 +
                         row['humidity'] * 0.3 - row['wind_speed'] *
                         2 + np.random.normal(0, 8))

        # Location effects
        location_effect = {'Urban': 10, 'Suburban': 0, 'Rural': -5}[row['location']]

        final_aqi = base_aqi + weather_effect + location_effect

        return np.clip(final_aqi, 0, 500)

    def _calculate_pollutant_aqi(self, concentration: float, pollutant: str) -> float:
        """Calculate AQI for a specific pollutant concentration"""
        if pollutant not in self.aqi_breakpoints:
            return 0
        
        breakpoints = self.aqi_breakpoints[pollutant]

        for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
            if bp_lo <= concentration <= bp_hi:
                return ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (concentration - bp_lo) + aqi_lo

        return 500

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess the data for model training/prediction"""
        logger.info("Preprocessing data...")
        df = df.copy()

        # Handle missing values for numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].median())

        # Handle missing values for categorical columns
        categorical_columns = df.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            if col != 'timestamp':
                df[col] = df[col].fillna(
                    df[col].mode()[0] if not df[col].mode().empty else "Unknown")

        # Create time features if requested
        if self.config['feature_engineering']['create_time_features'] and 'timestamp' in df.columns:
            df = self._create_time_features(df)

        # Create interaction features if requested
        if self.config['feature_engineering']['create_interactions']:
            df = self._create_interaction_features(df)

        # Define feature columns
        exclude_cols = ['timestamp', 'AQI'] if 'AQI' in df.columns else ['timestamp']
        self.feature_columns = [col for col in df.columns if col not in exclude_cols]

        # Identify categorical features
        self.categorical_features = [col for col in self.feature_columns
                                   if df[col].dtype == 'object' or df[col].dtype.name == 'category']

        logger.info(f"Preprocessing complete. Features: {len(self.feature_columns)}, "
                   f"Categorical: {len(self.categorical_features)}")

        return df

    def _create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features from timestamp"""
        if 'timestamp' not in df.columns:
            return df
        
        df = df.copy()
        
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_rush_hour'] = df['hour'].apply(lambda x: 1 if x in [7, 8, 9, 17, 18, 19] else 0)
        
        return df

    def _create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create interaction features between variables"""
        # Pollutant ratios
        if 'PM2.5' in df.columns and 'PM10' in df.columns:
            df['PM_ratio'] = df['PM2.5'] / (df['PM10'] + 1e-6)
        
        # Weather interactions
        if 'temperature' in df.columns and 'humidity' in df.columns:
            df['temp_humidity_interaction'] = df['temperature'] * df['humidity']
        
        if 'wind_speed' in df.columns and 'pressure' in df.columns:
            df['wind_pressure_interaction'] = df['wind_speed'] * df['pressure']
        
        # Pollution index
        pollutant_cols = ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3']
        available_pollutants = [col for col in pollutant_cols if col in df.columns]
        if available_pollutants:
            df['pollution_index'] = df[available_pollutants].mean(axis=1)
        
        return df

    def train_model(self, df: pd.DataFrame) -> Dict:
        """Train the CatBoost model"""
        logger.info('Starting model training...')

        df_processed = self.preprocess_data(df)

        X = df_processed[self.feature_columns]
        y = df_processed['AQI']

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=self.config['data_params']['test_size'],
            random_state=self.config['data_params']['random_state']
        )

        logger.info(f"Training set: {X_train.shape[0]} samples")
        logger.info(f"Test set: {X_test.shape[0]} samples")

        # Initialize model
        self.model = CatBoostRegressor(
            cat_features=self.categorical_features,
            **self.config['model_params']
        )

        # Create data pools
        train_pool = Pool(X_train, y_train, cat_features=self.categorical_features)
        test_pool = Pool(X_test, y_test, cat_features=self.categorical_features)

        # Train model
        self.model.fit(
            train_pool,
            eval_set=test_pool,
            early_stopping_rounds=50,
            plot=False
        )

        # Calculate metrics
        train_pred = self.model.predict(X_train)
        test_pred = self.model.predict(X_test)

        self.model_metrics = {
            'train_rmse': np.sqrt(mean_squared_error(y_train, train_pred)),
            'test_rmse': np.sqrt(mean_squared_error(y_test, test_pred)),
            'train_mae': mean_absolute_error(y_train, train_pred),
            'test_mae': mean_absolute_error(y_test, test_pred),
            'train_r2': r2_score(y_train, train_pred),
            'test_r2': r2_score(y_test, test_pred)
        }
        
        self.is_trained = True
        
        logger.info("Model training completed")
        logger.info(f"Test RMSE: {self.model_metrics['test_rmse']:.4f}")
        logger.info(f"Test R²: {self.model_metrics['test_r2']:.4f}")
        
        return self.model_metrics

    def predict(self, data: Union[pd.DataFrame, Dict]) -> Union[float, np.ndarray]:
        """Make predictions using the trained model"""
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train_model() first.")
        
        if isinstance(data, Dict):
            data = pd.DataFrame([data])

        data_processed = self.preprocess_data(data)
        X = data_processed[self.feature_columns]
        predictions = self.model.predict(X)

        if len(predictions) == 1:
            return float(predictions[0])
        
        return predictions

    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from the trained model"""
        if not self.is_trained:
            raise ValueError("Model is not trained yet.")
        
        importance = self.model.get_feature_importance()
        
        importance_df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        return importance_df

    def interpret_aqi(self, aqi_value: float) -> Dict:
        """Interpret AQI value and provide health recommendations"""
        if aqi_value <= 50:
            return {
                'category': 'Good',
                'color': '#00E400',
                'health_concern': 'None',
                'recommendation': 'Air quality is considered satisfactory, and air pollution poses little or no risk.'
            }
        elif aqi_value <= 100:
            return {
                'category': 'Moderate',
                'color': '#FFFF00',
                'health_concern': 'Unusually sensitive people',
                'recommendation': 'Air quality is acceptable; however, unusually sensitive people may experience minor issues.'
            }
        elif aqi_value <= 150:
            return {
                'category': 'Unhealthy for Sensitive Groups',
                'color': '#FF7E00',
                'health_concern': 'Sensitive groups',
                'recommendation': 'Members of sensitive groups may experience health effects. The general public is not likely to be affected.'
            }
        elif aqi_value <= 200:
            return {
                'category': 'Unhealthy',
                'color': '#FF0000',
                'health_concern': 'Everyone',
                'recommendation': 'Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects.'
            }
        elif aqi_value <= 300:
            return {
                'category': 'Very Unhealthy',
                'color': '#8F3F97',
                'health_concern': 'Everyone',
                'recommendation': 'Health warnings of emergency conditions. The entire population is more likely to be affected.'
            }
        else:
            return {
                'category': 'Hazardous',
                'color': '#7E0023',
                'health_concern': 'Everyone',
                'recommendation': 'Health alert: everyone may experience more serious health effects.'
            }

    def save_model(self, filepath: str):
        """Save trained model to file"""
        if not self.is_trained:
            raise ValueError("Model is not trained yet.")
        
        # Save CatBoost model
        self.model.save_model(filepath)
        
        # Save additional metadata
        metadata = {
            'feature_columns': self.feature_columns,
            'categorical_features': self.categorical_features,
            'model_metrics': self.model_metrics,
            'config': self.config
        }
        
        metadata_path = filepath.replace('.cbm', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {filepath}")
        logger.info(f"Metadata saved to {metadata_path}")

    def load_model(self, filepath: str):
        """Load trained model from file"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        # Load CatBoost model
        self.model = CatBoostRegressor()
        self.model.load_model(filepath)
        
        # Load metadata
        metadata_path = filepath.replace('.cbm', '_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            self.feature_columns = metadata['feature_columns']
            self.categorical_features = metadata['categorical_features']
            self.model_metrics = metadata['model_metrics']
            self.config = metadata['config']
        
        self.is_trained = True
        logger.info(f"Model loaded from {filepath}")

    def get_model_info(self) -> Dict:
        """Get comprehensive model information"""
        if not self.is_trained:
            return {"status": "Model not trained"}
        
        return {
            'status': 'Trained',
            'feature_count': len(self.feature_columns),
            'categorical_features_count': len(self.categorical_features),
            'model_metrics': self.model_metrics,
            'config': self.config,
            'feature_columns': self.feature_columns
        }


if __name__ == "__main__":
    # Initialize AQI system
    aqi_system = AirQualityIndex()
    
    # Generate sample data
    print("=== Generating Sample Data ===")
    sample_data = aqi_system.generate_sample_data(5000)
    print(f"Generated {len(sample_data)} samples")
    print(f"AQI range: {sample_data['AQI'].min():.1f} - {sample_data['AQI'].max():.1f}")
    
    # Train model
    print("\n=== Training Model ===")
    metrics = aqi_system.train_model(sample_data)
    print("Training metrics:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value:.4f}")
    
    # Feature importance
    print("\n=== Feature Importance ===")
    importance = aqi_system.get_feature_importance()
    print(importance.head(10))
    
    # Make predictions
    print("\n=== Making Predictions ===")
    test_data = {
        'PM2.5': 45.0,
        'PM10': 80.0,
        'NO2': 25.0,
        'SO2': 18.0,
        'CO': 1.5,
        'O3': 85.0,
        'temperature': 28.0,
        'humidity': 65.0,
        'wind_speed': 12.0,
        'pressure': 1015.0,
        'location': 'Urban',
        'season': 'Summer',
        'timestamp': datetime.now()
    }
    
    predicted_aqi = aqi_system.predict(test_data)
    interpretation = aqi_system.interpret_aqi(predicted_aqi)
    
    print(f"Predicted AQI: {predicted_aqi:.2f}")
    print(f"Category: {interpretation['category']}")
    print(f"Recommendation: {interpretation['recommendation']}")
    
    # Save model
    print("\n=== Saving Model ===")
    aqi_system.save_model("aqi_model.cbm")
    
    # Model info

    print("\n=== Model Information ===")
    model_info = aqi_system.get_model_info()
    print(f"Status: {model_info['status']}")
    print(f"Features: {model_info['feature_count']}")
    print(f"Test RMSE: {model_info['model_metrics']['test_rmse']:.4f}")
    print("\n=== AQI System Ready ===")


