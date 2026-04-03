"""
Model Recreation Script for Web App
This script recreates the models using the current sklearn version to avoid compatibility issues.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, classification_report
from xgboost import XGBClassifier
from imblearn.over_sampling import ADASYN
import warnings
warnings.filterwarnings('ignore')

def recreate_models():
    """Recreate the models with current sklearn version"""
    print("🔄 Recreating models with current sklearn version...")
    
    try:
        # Load the data
        print("📊 Loading data...")
        df = pd.read_csv('data/cleaned_credit_data.csv')
        
        X = df.drop(columns=['ID', 'TARGET'])
        y = df['TARGET']
        
        print(f"✅ Data loaded: {X.shape[0]} samples, {X.shape[1]} features")
        
        # Define columns
        cat_cols = ['CODE_GENDER', 'FLAG_OWN_CAR', 'FLAG_OWN_REALTY',
                    'NAME_INCOME_TYPE', 'NAME_EDUCATION_TYPE', 'NAME_FAMILY_STATUS',
                    'NAME_HOUSING_TYPE', 'OCCUPATION_TYPE']
        
        num_cols = ['CNT_CHILDREN', 'AMT_INCOME_TOTAL', 'CNT_FAM_MEMBERS',
                    'AGE_YEARS', 'EMPLOYED_YEARS']
        
        # Create preprocessor
        print("🔧 Creating preprocessor...")
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), num_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore'), cat_cols)
            ])
        
        # Split data
        print("📝 Splitting data...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y)
        
        # Fit preprocessor and transform data
        print("⚙️ Preprocessing data...")
        X_train_transformed = preprocessor.fit_transform(X_train)
        X_test_transformed = preprocessor.transform(X_test)
        
        # Apply ADASYN
        print("🔄 Applying ADASYN...")
        adasyn = ADASYN(random_state=42)
        X_train_adasyn, y_train_adasyn = adasyn.fit_resample(X_train_transformed, y_train)
        
        print(f"   Original: {X_train_transformed.shape[0]} samples")
        print(f"   After ADASYN: {X_train_adasyn.shape[0]} samples")
        
        # Create individual models
        print("🤖 Training individual models...")
        
        # Risk model (conservative parameters)
        risk_model = XGBClassifier(
            objective='binary:logistic',
            scale_pos_weight=100,
            max_depth=8,
            min_child_weight=0.1,
            gamma=0.3,
            subsample=0.8,
            colsample_bytree=0.8,
            learning_rate=0.05,
            n_estimators=400,
            reg_alpha=0.2,
            reg_lambda=1.5,
            random_state=42,
            use_label_encoder=False,
            eval_metric='auc',
            n_jobs=-1
        )
        
        # Focal loss model
        xgb_focal = XGBClassifier(
            objective='binary:logistic',
            scale_pos_weight=200,
            max_depth=8,
            min_child_weight=0.5,
            gamma=0.5,
            subsample=0.7,
            colsample_bytree=0.7,
            learning_rate=0.05,
            n_estimators=500,
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss',
            reg_alpha=0.1,
            reg_lambda=1.0
        )
        
        # Weighted model
        neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
        scale_pos_weight = neg / pos
        
        xgb_weighted = XGBClassifier(
            objective='binary:logistic',
            scale_pos_weight=scale_pos_weight * 3,
            max_depth=6,
            min_child_weight=1,
            gamma=0.2,
            subsample=0.8,
            colsample_bytree=0.8,
            learning_rate=0.05,
            n_estimators=300,
            random_state=42,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        
        # Train individual models
        print("   Training risk model...")
        risk_model.fit(X_train_adasyn, y_train_adasyn)
        
        print("   Training focal model...")
        xgb_focal.fit(X_train_adasyn, y_train_adasyn)
        
        print("   Training weighted model...")
        xgb_weighted.fit(X_train_transformed, y_train)
        
        # Create ensemble
        print("🎯 Creating ensemble model...")
        risk_ensemble = VotingClassifier(
            estimators=[
                ('xgb_risk', risk_model),
                ('xgb_focal', xgb_focal),
                ('xgb_weighted', xgb_weighted)
            ],
            voting='soft'
        )
        
        # Train ensemble
        print("   Training ensemble...")
        risk_ensemble.fit(X_train_adasyn, y_train_adasyn)
        
        # Test the model
        print("🧪 Testing model...")
        y_proba = risk_ensemble.predict_proba(X_test_transformed)[:, 1]
        
        # Use conservative threshold
        optimal_threshold = 0.90
        y_pred = (y_proba >= optimal_threshold).astype(int)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
        recall = recall_score(y_test, y_pred, pos_label=1)
        
        print(f"   ✅ Accuracy: {accuracy:.3f}")
        print(f"   ✅ Precision: {precision:.3f}")
        print(f"   ✅ Recall: {recall:.3f}")
        
        # Save models
        print("💾 Saving models...")
        models_dir = 'models'
        os.makedirs(models_dir, exist_ok=True)
        
        # Save with current sklearn version
        joblib.dump(risk_ensemble, f'{models_dir}/risk_ensemble_model.pkl')
        joblib.dump(preprocessor, f'{models_dir}/preprocessor.pkl')
        
        # Save parameters
        model_params = {
            'optimal_threshold': optimal_threshold,
            'cost_false_positive': 1,
            'cost_false_negative': 10,
            'model_performance': {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'threshold': optimal_threshold
            }
        }
        
        joblib.dump(model_params, f'{models_dir}/model_parameters.pkl')
        
        print("✅ Models saved successfully!")
        print(f"   📁 Location: {os.path.abspath(models_dir)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error recreating models: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Model Recreation for Credit Approval Web App")
    print("=" * 50)
    
    if recreate_models():
        print("\n🎉 Success! Models recreated and saved.")
        print("Now you can run: python app.py")
    else:
        print("\n❌ Failed to recreate models.")
        print("Please check the error messages above.")
