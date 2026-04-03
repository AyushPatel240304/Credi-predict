#!/usr/bin/env python3
"""
Credit Approval Web App Setup Script
"""

import os
import subprocess
import sys

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def install_requirements():
    """Install required packages"""
    print("\n📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install packages")
        return False

def check_models():
    """Check if models are available"""
    models_dir = 'models'
    required_files = [
        'risk_ensemble_model.pkl',
        'preprocessor.pkl',
        'model_parameters.pkl'
    ]
    
    if not os.path.exists(models_dir):
        print(f"❌ Models directory '{models_dir}' not found")
        print("💡 Please run the notebook to train and save models first")
        return False
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(models_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing model files: {missing_files}")
        print("💡 Please run the notebook to train and save models first")
        return False
    
    print("✅ All model files found")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'models']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    print("✅ Directories created")

def main():
    """Main setup function"""
    print("🚀 Credit Approval Web App Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Create directories
    create_directories()
    
    # Install requirements
    if not install_requirements():
        return
    
    # Check models
    if not check_models():
        print("\n⚠️  Setup incomplete - models not found")
        print("To complete setup:")
        print("1. Open notebooks/preprocessing-feature-engineering.ipynb")
        print("2. Run all cells to train the models")
        print("3. Run the last cell to save models")
        print("4. Then run: python app.py")
        return
    
    print("\n🎉 Setup complete!")
    print("\nTo start the web application:")
    print("1. Run: python app.py")
    print("2. Open: http://localhost:5000")
    print("3. Try single applications or upload CSV files")
    
    # Ask if user wants to start the app
    response = input("\nStart the web app now? (y/n): ").lower().strip()
    if response in ['y', 'yes']:
        print("\n🌐 Starting web application...")
        try:
            os.system('python app.py')
        except KeyboardInterrupt:
            print("\n👋 Web app stopped")

if __name__ == "__main__":
    main()
