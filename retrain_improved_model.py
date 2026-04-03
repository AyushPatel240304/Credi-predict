"""
Improved model retraining script with better class balance handling
and feature importance analysis
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from imblearn.over_sampling import ADASYN, SMOTE
from imblearn.under_sampling import EditedNearestNeighbours
from imblearn.combine import SMOTEENN
import joblib
import warnings
warnings.filterwarnings('ignore')

def load_and_prepare_data():
    """Load and prepare the credit data"""
    print("📂 Loading data...")
    
    # Load the datasets
    app_df = pd.read_csv('data/application_record.csv')
    credit_df = pd.read_csv('data/credit_record.csv')
    
    print(f"Application records: {len(app_df)}")
    print(f"Credit records: {len(credit_df)}")
    
    # Create target variable based on credit history
    # Count overdue instances (>= 2 months late)
    overdue_counts = credit_df[credit_df['STATUS'].isin(['2', '3', '4', '5'])].groupby('ID').size()
    
    # More aggressive labeling - anyone with 2+ overdue months is bad
    bad_clients = overdue_counts[overdue_counts >= 2].index
    
    # Create target
    app_df['TARGET'] = 0  # Good by default
    app_df.loc[app_df['ID'].isin(bad_clients), 'TARGET'] = 1  # Bad
    
    print(f"Bad clients (TARGET=1): {app_df['TARGET'].sum()} ({app_df['TARGET'].mean()*100:.1f}%)")
    print(f"Good clients (TARGET=0): {(app_df['TARGET']==0).sum()} ({(app_df['TARGET']==0).mean()*100:.1f}%)")
    
    return app_df

def feature_engineering(df):
    """Enhanced feature engineering"""
    print("🔧 Feature engineering...")
    
    # Create age from days
    df['AGE_YEARS'] = abs(df['DAYS_BIRTH']) // 365
    df['EMPLOYED_YEARS'] = abs(df['DAYS_EMPLOYED']) // 365
    
    # Cap unrealistic employment years
    df.loc[df['EMPLOYED_YEARS'] > df['AGE_YEARS'], 'EMPLOYED_YEARS'] = df['AGE_YEARS']
    df.loc[df['EMPLOYED_YEARS'] > 50, 'EMPLOYED_YEARS'] = 50
    
    # Income to age ratio
    df['INCOME_PER_PERSON'] = df['AMT_INCOME_TOTAL'] / df['CNT_FAM_MEMBERS']
    df['INCOME_PER_CHILD'] = df['AMT_INCOME_TOTAL'] / (df['CNT_CHILDREN'] + 1)
    
    # Employment stability
    df['EMPLOYMENT_RATIO'] = df['EMPLOYED_YEARS'] / (df['AGE_YEARS'] + 1)
    
    # Risk categories
    df['HIGH_CHILDREN'] = (df['CNT_CHILDREN'] >= 3).astype(int)
    df['LOW_INCOME'] = (df['AMT_INCOME_TOTAL'] < 100000).astype(int)
    df['YOUNG_AGE'] = (df['AGE_YEARS'] < 25).astype(int)
    df['NO_EMPLOYMENT'] = (df['EMPLOYED_YEARS'] <= 1).astype(int)
    
    # Select features
    features = [
        'CODE_GENDER', 'FLAG_OWN_CAR', 'FLAG_OWN_REALTY',
        'CNT_CHILDREN', 'AMT_INCOME_TOTAL', 'NAME_INCOME_TYPE',
        'NAME_EDUCATION_TYPE', 'NAME_FAMILY_STATUS', 'NAME_HOUSING_TYPE',
        'CNT_FAM_MEMBERS', 'OCCUPATION_TYPE', 'AGE_YEARS', 'EMPLOYED_YEARS',
        'INCOME_PER_PERSON', 'INCOME_PER_CHILD', 'EMPLOYMENT_RATIO',
        'HIGH_CHILDREN', 'LOW_INCOME', 'YOUNG_AGE', 'NO_EMPLOYMENT'
    ]
    
    return df[features + ['TARGET']].copy()

def create_preprocessor():
    """Create preprocessing pipeline"""
    print("⚙️ Creating preprocessor...")
    
    categorical_features = [
        'CODE_GENDER', 'FLAG_OWN_CAR', 'FLAG_OWN_REALTY',
        'NAME_INCOME_TYPE', 'NAME_EDUCATION_TYPE', 'NAME_FAMILY_STATUS',
        'NAME_HOUSING_TYPE', 'OCCUPATION_TYPE'
    ]
    
    numerical_features = [
        'CNT_CHILDREN', 'AMT_INCOME_TOTAL', 'CNT_FAM_MEMBERS', 
        'AGE_YEARS', 'EMPLOYED_YEARS', 'INCOME_PER_PERSON',
        'INCOME_PER_CHILD', 'EMPLOYMENT_RATIO', 'HIGH_CHILDREN',
        'LOW_INCOME', 'YOUNG_AGE', 'NO_EMPLOYMENT'
    ]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features),
            ('cat', OneHotEncoder(drop='first', handle_unknown='ignore'), categorical_features)
        ]
    )
    
    return preprocessor

def train_improved_models(X_train, y_train, X_test, y_test):
    """Train improved ensemble models with better parameters"""
    print("🎯 Training improved models...")
    
    # Individual models with better parameters for imbalanced data
    models = {
        'rf': RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42
        ),
        'gb': GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=8,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42
        ),
        'lr': LogisticRegression(
            C=0.1,
            class_weight='balanced',
            random_state=42,
            max_iter=1000
        )
    }
    
    # Train individual models and evaluate
    trained_models = {}
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train)
        
        # Evaluate
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        auc_score = roc_auc_score(y_test, y_pred_proba)
        
        print(f"  {name} - Train: {train_score:.3f}, Test: {test_score:.3f}, AUC: {auc_score:.3f}")
        trained_models[name] = model
    
    # Create ensemble
    ensemble = VotingClassifier(
        estimators=[(name, model) for name, model in trained_models.items()],
        voting='soft'
    )
    
    print("Training ensemble...")
    ensemble.fit(X_train, y_train)
    
    return ensemble, trained_models

def evaluate_model(model, X_test, y_test):
    """Comprehensive model evaluation"""
    print("\n📊 Model Evaluation:")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Basic metrics
    accuracy = model.score(X_test, y_test)
    auc_score = roc_auc_score(y_test, y_pred_proba)
    
    print(f"Accuracy: {accuracy:.3f}")
    print(f"AUC Score: {auc_score:.3f}")
    
    # Classification report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Confusion matrix
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Test different thresholds
    print("\nThreshold Analysis:")
    thresholds = [0.3, 0.5, 0.7, 0.9]
    for threshold in thresholds:
        y_pred_thresh = (y_pred_proba >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred_thresh).ravel()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        print(f"  Threshold {threshold}: Precision: {precision:.3f}, Recall: {recall:.3f}")
    
    return y_pred_proba

def test_extreme_cases(model, preprocessor):
    """Test model with extreme cases to ensure it's working properly"""
    print("\n🧪 Testing extreme cases:")
    
    # Extreme high-risk case
    high_risk = {
        'CODE_GENDER': 'M',
        'FLAG_OWN_CAR': 'N',
        'FLAG_OWN_REALTY': 'N',
        'CNT_CHILDREN': 5,
        'AMT_INCOME_TOTAL': 50000,  # Very low income
        'NAME_INCOME_TYPE': 'Working',
        'NAME_EDUCATION_TYPE': 'Lower secondary',
        'NAME_FAMILY_STATUS': 'Single / not married',
        'NAME_HOUSING_TYPE': 'With parents',
        'CNT_FAM_MEMBERS': 6,
        'OCCUPATION_TYPE': 'Laborers',
        'AGE_YEARS': 23,  # Young
        'EMPLOYED_YEARS': 1,  # Little experience
        'INCOME_PER_PERSON': 50000/6,
        'INCOME_PER_CHILD': 50000/6,
        'EMPLOYMENT_RATIO': 1/23,
        'HIGH_CHILDREN': 1,
        'LOW_INCOME': 1,
        'YOUNG_AGE': 1,
        'NO_EMPLOYMENT': 1
    }
    
    # Extreme low-risk case
    low_risk = {
        'CODE_GENDER': 'M',
        'FLAG_OWN_CAR': 'Y',
        'FLAG_OWN_REALTY': 'Y',
        'CNT_CHILDREN': 1,
        'AMT_INCOME_TOTAL': 300000,  # High income
        'NAME_INCOME_TYPE': 'Working',
        'NAME_EDUCATION_TYPE': 'Higher education',
        'NAME_FAMILY_STATUS': 'Married',
        'NAME_HOUSING_TYPE': 'House / apartment',
        'CNT_FAM_MEMBERS': 3,
        'OCCUPATION_TYPE': 'Managers',
        'AGE_YEARS': 45,  # Mature
        'EMPLOYED_YEARS': 20,  # Experienced
        'INCOME_PER_PERSON': 300000/3,
        'INCOME_PER_CHILD': 300000/2,
        'EMPLOYMENT_RATIO': 20/45,
        'HIGH_CHILDREN': 0,
        'LOW_INCOME': 0,
        'YOUNG_AGE': 0,
        'NO_EMPLOYMENT': 0
    }
    
    for case_name, case_data in [("High Risk", high_risk), ("Low Risk", low_risk)]:
        df_case = pd.DataFrame([case_data])
        X_case = preprocessor.transform(df_case)
        proba = model.predict_proba(X_case)[0]
        
        print(f"  {case_name}: Good={proba[0]:.3f}, Bad={proba[1]:.3f}")

def main():
    """Main training pipeline"""
    print("🚀 Starting improved model training...")
    
    # Load and prepare data
    df = load_and_prepare_data()
    
    # Feature engineering
    df_features = feature_engineering(df)
    
    # Remove rows with missing values
    df_features = df_features.dropna()
    print(f"Final dataset size: {len(df_features)}")
    
    # Split features and target
    X = df_features.drop('TARGET', axis=1)
    y = df_features['TARGET']
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Create preprocessor
    preprocessor = create_preprocessor()
    
    # Fit preprocessor and transform data
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    
    # Apply SMOTEENN for better class balance
    print("🔄 Applying SMOTEENN resampling...")
    smoteenn = SMOTEENN(random_state=42)
    X_train_resampled, y_train_resampled = smoteenn.fit_resample(X_train_processed, y_train)
    
    print(f"Original train set: {len(y_train)} samples")
    print(f"Resampled train set: {len(y_train_resampled)} samples")
    print(f"Class 0: {(y_train_resampled==0).sum()}, Class 1: {(y_train_resampled==1).sum()}")
    
    # Train models
    ensemble, individual_models = train_improved_models(
        X_train_resampled, y_train_resampled, X_test_processed, y_test
    )
    
    # Evaluate
    y_pred_proba = evaluate_model(ensemble, X_test_processed, y_test)
    
    # Test extreme cases
    test_extreme_cases(ensemble, preprocessor)
    
    # Save models
    print("\n💾 Saving models...")
    joblib.dump(ensemble, 'models/risk_ensemble_model.pkl')
    joblib.dump(preprocessor, 'models/preprocessor.pkl')
    
    # Save individual models too
    for name, model in individual_models.items():
        joblib.dump(model, f'models/{name}_model.pkl')
    
    print("✅ Models saved successfully!")
    print("\n🎯 Training completed!")

if __name__ == "__main__":
    main()
