"""
Form Validation Service for Credit Applications
Provides comprehensive server-side validation with logical consistency checks
"""

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class FormValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_credit_application(self, form_data: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Comprehensive validation of credit application form data
        Returns: (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Basic field validations
        self._validate_personal_info(form_data)
        self._validate_income_employment(form_data)
        self._validate_family_info(form_data)
        self._validate_assets(form_data)
        
        # Logical consistency checks
        self._validate_logical_consistency(form_data)
        
        # Business rule validations
        self._validate_business_rules(form_data)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_personal_info(self, data: Dict):
        """Validate personal information fields"""
        
        # Age validation
        age = self._get_int_value(data, 'age')
        if age is not None:
            if age < 18:
                self.errors.append("Applicant must be at least 18 years old")
            elif age > 100:
                self.errors.append("Please enter a valid age")
            elif age < 21:
                self.warnings.append("Young applicants may face additional requirements")
        else:
            self.errors.append("Age is required")
        
        # Gender validation
        gender = data.get('gender', '').strip()
        if not gender:
            self.errors.append("Gender is required")
        elif gender not in ['M', 'F']:
            self.errors.append("Gender must be Male (M) or Female (F)")
        
        # Family status validation
        family_status = data.get('family_status', '').strip()
        valid_family_statuses = [
            'Single / not married', 'Married', 'Civil marriage', 
            'Widow', 'Separated'
        ]
        if not family_status:
            self.errors.append("Family status is required")
        elif family_status not in valid_family_statuses:
            self.errors.append("Invalid family status")
    
    def _validate_income_employment(self, data: Dict):
        """Validate income and employment information"""
        
        # Income validation
        income = self._get_float_value(data, 'income')
        if income is not None:
            if income < 0:
                self.errors.append("Income cannot be negative")
            elif income > 10000000:  # 10 million cap
                self.warnings.append("Please verify this unusually high income amount")
            elif income < 12000:
                self.warnings.append("Low income may affect approval chances")
        else:
            self.errors.append("Annual income is required")
        
        # Income type validation
        income_type = data.get('income_type', '').strip()
        valid_income_types = [
            'Working', 'State servant', 'Commercial associate', 
            'Pensioner', 'Unemployed', 'Student', 'Businessman', 
            'Maternity leave'
        ]
        if not income_type:
            self.errors.append("Income type is required")
        elif income_type not in valid_income_types:
            self.errors.append("Invalid income type")
        
        # Employment days validation
        employment_days = self._get_int_value(data, 'employment_days')
        if employment_days is not None:
            if income_type == 'Unemployed' and employment_days > 0:
                self.errors.append("Employment days should be negative if unemployed")
            elif income_type != 'Unemployed' and employment_days < 0:
                self.errors.append("Employment days should be positive if employed")
            elif employment_days < -10950:  # 30 years unemployment
                self.warnings.append("Extended unemployment period may affect approval")
            elif employment_days > 0 and employment_days < 90:
                self.warnings.append("Short employment history may require additional verification")
        else:
            self.errors.append("Employment days is required")
        
        # Education validation
        education = data.get('education_type', '').strip()
        valid_educations = [
            'Secondary / secondary special', 'Higher education', 
            'Incomplete higher', 'Lower secondary', 'Academic degree'
        ]
        if not education:
            self.errors.append("Education level is required")
        elif education not in valid_educations:
            self.errors.append("Invalid education level")
    
    def _validate_family_info(self, data: Dict):
        """Validate family-related information"""
        
        # Children validation
        children = self._get_int_value(data, 'children')
        if children is not None:
            if children < 0:
                self.errors.append("Number of children cannot be negative")
            elif children > 15:
                self.warnings.append("Large number of dependents may affect assessment")
        else:
            self.errors.append("Number of children is required")
        
        # Family members validation
        family_members = self._get_int_value(data, 'family_members')
        if family_members is not None:
            if family_members < 1:
                self.errors.append("Family size must be at least 1")
            elif family_members > 20:
                self.warnings.append("Unusually large family size")
            elif children is not None and family_members <= children:
                self.errors.append("Family size must be larger than number of children")
        else:
            self.errors.append("Family size is required")
    
    def _validate_assets(self, data: Dict):
        """Validate asset-related information"""
        
        # Car ownership validation
        own_car = data.get('own_car', '').strip()
        if not own_car:
            self.errors.append("Car ownership status is required")
        elif own_car not in ['Y', 'N']:
            self.errors.append("Car ownership must be Y or N")
        
        # Real estate ownership validation
        own_realty = data.get('own_realty', '').strip()
        if not own_realty:
            self.errors.append("Real estate ownership status is required")
        elif own_realty not in ['Y', 'N']:
            self.errors.append("Real estate ownership must be Y or N")
        
        # Housing type validation
        housing_type = data.get('housing_type', '').strip()
        valid_housing_types = [
            'House / apartment', 'With parents', 'Municipal apartment',
            'Rented apartment', 'Office apartment', 'Co-op apartment'
        ]
        if not housing_type:
            self.errors.append("Housing type is required")
        elif housing_type not in valid_housing_types:
            self.errors.append("Invalid housing type")
    
    def _validate_logical_consistency(self, data: Dict):
        """Check for logical consistency between fields"""
        
        age = self._get_int_value(data, 'age')
        income = self._get_float_value(data, 'income')
        education = data.get('education_type', '')
        income_type = data.get('income_type', '')
        family_status = data.get('family_status', '')
        children = self._get_int_value(data, 'children', 0)
        family_members = self._get_int_value(data, 'family_members', 1)
        
        # Age vs Education consistency
        if age and education:
            if age < 22 and education == 'Higher education':
                self.warnings.append("Higher education unusual for age under 22")
            elif age < 25 and education == 'Academic degree':
                self.warnings.append("Academic degree unusual for age under 25")
            elif age > 65 and education == 'Lower secondary':
                # This is actually normal, just noting
                pass
        
        # Age vs Income Type consistency
        if age and income_type:
            if age < 65 and income_type == 'Pensioner':
                self.warnings.append("Early retirement may require additional documentation")
            elif age > 30 and income_type == 'Student':
                self.warnings.append("Student status unusual for this age group")
            elif age < 18 and income_type != 'Student':
                self.errors.append("Minors should typically be students")
        
        # Income vs Age consistency
        if age and income:
            if age < 25 and income > 150000:
                self.warnings.append("Very high income unusual for young age - please verify")
            elif age > 65 and income > 200000 and income_type != 'Businessman':
                self.warnings.append("High income unusual for retirement age")
        
        # Family consistency checks
        if family_status and children is not None and family_members:
            if family_status == 'Single / not married':
                if family_members > children + 1:
                    self.warnings.append("Family size seems large for single status")
                elif children > 4:
                    self.warnings.append("Single parent with many children may need additional support documentation")
            elif family_status == 'Married':
                if family_members < children + 2:
                    self.warnings.append("Family size seems small for married status with children")
        
        # Income vs Employment consistency
        if income and income_type:
            if income_type == 'Unemployed' and income > 20000:
                self.warnings.append("High income unusual for unemployed status")
            elif income_type == 'Student' and income > 50000:
                self.warnings.append("High income unusual for student status")
            elif income_type == 'Maternity leave' and income > 100000:
                self.warnings.append("Very high income unusual during maternity leave")
    
    def _validate_business_rules(self, data: Dict):
        """Apply business-specific validation rules"""
        
        age = self._get_int_value(data, 'age')
        income = self._get_float_value(data, 'income')
        employment_days = self._get_int_value(data, 'employment_days')
        children = self._get_int_value(data, 'children', 0)
        income_type = data.get('income_type', '')
        
        # Minimum income requirements
        if income is not None:
            min_income = 15000  # Base minimum
            if children:
                min_income += children * 5000  # Additional per child
            
            if income < min_income:
                self.warnings.append(f"Income below recommended minimum of ${min_income:,} for family size")
        
        # Employment stability requirements
        if employment_days is not None and income_type not in ['Pensioner', 'Student']:
            if employment_days < 180 and employment_days > 0:
                self.warnings.append("Short employment history may require additional verification")
            elif employment_days < 0 and abs(employment_days) > 1095:  # 3 years unemployed
                self.warnings.append("Long unemployment period may significantly affect approval")
        
        # Age-related business rules
        if age is not None:
            if age > 70:
                self.warnings.append("Advanced age may require additional health and income verification")
            elif age < 21:
                self.warnings.append("Young applicants may need a co-signer or additional documentation")
        
        # Risk factor combinations
        risk_factors = 0
        if income and income < 25000:
            risk_factors += 1
        if employment_days and employment_days < 365:
            risk_factors += 1
        if children and children > 3:
            risk_factors += 1
        if age and age < 25:
            risk_factors += 1
        
        if risk_factors >= 3:
            self.warnings.append("Multiple risk factors detected - consider improving financial stability before applying")
    
    def _get_int_value(self, data: Dict, key: str, default: Optional[int] = None) -> Optional[int]:
        """Safely get integer value from form data"""
        try:
            value = data.get(key)
            if value is None or value == '':
                return default
            return int(value)
        except (ValueError, TypeError):
            self.errors.append(f"Invalid numeric value for {key}")
            return None
    
    def _get_float_value(self, data: Dict, key: str, default: Optional[float] = None) -> Optional[float]:
        """Safely get float value from form data"""
        try:
            value = data.get(key)
            if value is None or value == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            self.errors.append(f"Invalid numeric value for {key}")
            return None
    
    def format_validation_summary(self) -> str:
        """Format validation results for display"""
        summary = []
        
        if self.errors:
            summary.append("❌ Errors found:")
            for error in self.errors:
                summary.append(f"  • {error}")
        
        if self.warnings:
            summary.append("⚠️  Warnings:")
            for warning in self.warnings:
                summary.append(f"  • {warning}")
        
        if not self.errors and not self.warnings:
            summary.append("✅ All validations passed!")
        
        return "\n".join(summary)
