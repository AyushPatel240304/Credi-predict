"""
AI Feedback Service for Credit Applications
Provides detailed feedback and suggestions using free AI APIs
"""

import requests
import json
import os
from typing import Dict, List, Optional

class AIFeedbackService:
    def __init__(self):
        self.hf_token = os.getenv('HF_API_TOKEN')
        self.use_local_ai = os.getenv('USE_LOCAL_AI', 'false').lower() == 'true'
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        
        # Hugging Face free models
        self.hf_models = [
            "microsoft/DialoGPT-large",
            "facebook/blenderbot-400M-distill",
            "microsoft/DialoGPT-medium"
        ]
    
    def generate_detailed_feedback(self, applicant_data: Dict, prediction_result: Dict) -> Dict:
        """
        Generate comprehensive feedback and suggestions for credit improvement
        """
        try:
            # Prepare context for AI
            context = self._prepare_context(applicant_data, prediction_result)
            
            if self.use_local_ai:
                feedback = self._get_local_ai_feedback(context)
            else:
                feedback = self._get_free_ai_feedback(context)
            
            return self._structure_feedback(feedback, applicant_data, prediction_result)
            
        except Exception as e:
            print(f"AI Feedback Error: {str(e)}")
            return self._get_fallback_feedback(applicant_data, prediction_result)
    
    def _prepare_context(self, applicant_data: Dict, prediction_result: Dict) -> str:
        """Prepare context for AI model"""
        decision = prediction_result.get('recommendation', {}).get('decision', 'UNKNOWN')
        risk_level = prediction_result.get('risk_level', 'UNKNOWN')
        risk_probability = prediction_result.get('risk_probability', 0)
        
        context = f"""
        Credit Application Analysis:
        
        Applicant Profile:
        - Age: {applicant_data.get('AGE_YEARS', 'N/A')} years
        - Income: ${applicant_data.get('AMT_INCOME_TOTAL', 'N/A'):,}
        - Education: {applicant_data.get('NAME_EDUCATION_TYPE', 'N/A')}
        - Employment: {applicant_data.get('NAME_INCOME_TYPE', 'N/A')}
        - Family Status: {applicant_data.get('NAME_FAMILY_STATUS', 'N/A')}
        - Children: {applicant_data.get('CNT_CHILDREN', 'N/A')}
        - Car Owner: {applicant_data.get('FLAG_OWN_CAR', 'N/A')}
        - Property Owner: {applicant_data.get('FLAG_OWN_REALTY', 'N/A')}
        
        Assessment Result:
        - Decision: {decision}
        - Risk Level: {risk_level}
        - Risk Probability: {risk_probability}%
        
        Please provide detailed financial advice and specific actionable steps to improve creditworthiness.
        """
        
        return context
    
    def _get_free_ai_feedback(self, context: str) -> str:
        """Get feedback using free Hugging Face API"""
        try:
            # Use a simple approach without API if no token
            if not self.hf_token or self.hf_token == 'your_free_huggingface_token_here':
                return self._get_rule_based_feedback(context)
            
            # Try Hugging Face Inference API
            headers = {
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "application/json"
            }
            
            prompt = f"As a financial advisor, analyze this credit profile and provide specific improvement suggestions:\n\n{context}\n\nAdvice:"
            
            for model in self.hf_models:
                try:
                    api_url = f"https://api-inference.huggingface.co/models/{model}"
                    response = requests.post(
                        api_url,
                        headers=headers,
                        json={"inputs": prompt[:500]},  # Limit input length
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, list) and len(result) > 0:
                            return result[0].get('generated_text', '').replace(prompt, '').strip()
                        
                except Exception as e:
                    print(f"HF Model {model} failed: {str(e)}")
                    continue
            
            # Fallback to rule-based if all models fail
            return self._get_rule_based_feedback(context)
            
        except Exception as e:
            print(f"Free AI API Error: {str(e)}")
            return self._get_rule_based_feedback(context)
    
    def _get_local_ai_feedback(self, context: str) -> str:
        """Get feedback using local Ollama (completely free)"""
        try:
            prompt = f"As a financial advisor, analyze this credit profile and provide specific improvement suggestions:\n\n{context}"
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama2",  # or any other local model
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            
        except Exception as e:
            print(f"Local AI Error: {str(e)}")
            
        return self._get_rule_based_feedback(context)
    
    def _get_rule_based_feedback(self, context: str) -> str:
        """Rule-based feedback as fallback (always works)"""
        # This provides intelligent feedback without requiring any external API
        feedback_parts = [
            "Based on your credit profile analysis, here are personalized recommendations:",
            "",
            "🎯 **Priority Actions:**",
            "• Maintain consistent payment history - this is the most important factor",
            "• Keep credit utilization below 30% of available limits",
            "• Avoid applying for multiple credit products simultaneously",
            "",
            "💰 **Income & Employment:**",
            "• Consider additional income sources or side work",
            "• Maintain stable employment history",
            "• Document all income sources properly",
            "",
            "🏠 **Assets & Stability:**",
            "• Property ownership significantly improves creditworthiness",
            "• Maintain savings for emergency funds",
            "• Keep important financial documents organized",
            "",
            "📊 **Credit Building:**",
            "• Start with secured credit cards if needed",
            "• Pay all bills on time, including utilities",
            "• Monitor your credit report regularly",
            "",
            "⏰ **Timeline:**",
            "• Credit improvements typically show in 3-6 months",
            "• Major improvements may take 6-12 months",
            "• Be patient and consistent with good financial habits"
        ]
        
        return "\n".join(feedback_parts)
    
    def _structure_feedback(self, raw_feedback: str, applicant_data: Dict, prediction_result: Dict) -> Dict:
        """Structure the AI feedback into organized sections"""
        
        # Enhanced analysis based on specific data
        priority_actions = []
        income_advice = []
        asset_advice = []
        timeline_advice = []
        
        # Analyze specific conditions
        income = applicant_data.get('AMT_INCOME_TOTAL', 0)
        has_car = applicant_data.get('FLAG_OWN_CAR') == 'Y'
        has_property = applicant_data.get('FLAG_OWN_REALTY') == 'Y'
        age = applicant_data.get('AGE_YEARS', 0)
        children = applicant_data.get('CNT_CHILDREN', 0)
        
        # Income-specific advice
        if income < 30000:
            income_advice.extend([
                "Consider skill development for higher-paying opportunities",
                "Look into part-time or freelance work to supplement income",
                "Explore government assistance programs if eligible"
            ])
        elif income < 60000:
            income_advice.extend([
                "Focus on career advancement and professional development",
                "Consider additional certifications in your field",
                "Build a side income stream for financial stability"
            ])
        else:
            income_advice.extend([
                "Maintain current income stability",
                "Consider investment opportunities for wealth building",
                "Optimize tax strategies to maximize take-home income"
            ])
        
        # Asset-specific advice
        if not has_property and not has_car:
            asset_advice.extend([
                "Start building toward homeownership or vehicle purchase",
                "Consider a secured loan to establish credit history",
                "Focus on saving for down payments"
            ])
        elif not has_property:
            asset_advice.extend([
                "Property ownership would significantly improve your profile",
                "Research first-time buyer programs",
                "Consider starting with a smaller property or condo"
            ])
        
        # Age and family considerations
        if age < 25:
            priority_actions.extend([
                "Focus on building credit history early",
                "Establish stable employment patterns",
                "Avoid accumulating unnecessary debt"
            ])
        
        if children > 0:
            priority_actions.extend([
                "Ensure adequate life and health insurance coverage",
                "Build emergency funds for family security",
                "Consider education savings plans"
            ])
        
        # Timeline based on current risk level
        risk_level = prediction_result.get('risk_level', 'MEDIUM')
        if risk_level in ['HIGH', 'VERY HIGH']:
            timeline_advice.extend([
                "Focus on immediate debt reduction",
                "Expect 6-12 months for significant improvement",
                "Consider credit counseling services"
            ])
        else:
            timeline_advice.extend([
                "Continue current positive financial habits",
                "Minor improvements possible in 3-6 months",
                "Focus on optimization rather than major changes"
            ])
        
        return {
            'ai_generated_text': raw_feedback,
            'structured_advice': {
                'priority_actions': priority_actions or [
                    "Maintain consistent payment history",
                    "Keep credit utilization low",
                    "Monitor credit report regularly"
                ],
                'income_optimization': income_advice or [
                    "Focus on stable employment",
                    "Document all income sources",
                    "Consider additional income streams"
                ],
                'asset_building': asset_advice or [
                    "Consider property ownership when possible",
                    "Maintain existing assets properly",
                    "Build emergency savings"
                ],
                'timeline_expectations': timeline_advice or [
                    "Credit improvements typically show in 3-6 months",
                    "Major changes may take 6-12 months",
                    "Consistency is key to success"
                ]
            },
            'personalized_score': self._calculate_improvement_score(applicant_data, prediction_result),
            'next_review_date': "90 days recommended for reassessment"
        }
    
    def _calculate_improvement_score(self, applicant_data: Dict, prediction_result: Dict) -> Dict:
        """Calculate improvement potential score"""
        
        current_risk = prediction_result.get('risk_probability', 50)
        
        # Calculate improvement potential based on various factors
        improvement_factors = []
        
        income = applicant_data.get('AMT_INCOME_TOTAL', 0)
        if income < 40000:
            improvement_factors.append(("Income Growth Potential", 25))
        
        if applicant_data.get('FLAG_OWN_REALTY') != 'Y':
            improvement_factors.append(("Property Ownership Impact", 20))
        
        if applicant_data.get('AGE_YEARS', 0) < 30:
            improvement_factors.append(("Credit History Building", 15))
        
        employment_days = applicant_data.get('EMPLOYED_YEARS', 0)
        if employment_days < 365:  # Less than 1 year
            improvement_factors.append(("Employment Stability", 20))
        
        max_improvement = sum([factor[1] for factor in improvement_factors])
        potential_new_risk = max(5, current_risk - max_improvement)
        
        return {
            'current_risk_percentage': current_risk,
            'potential_risk_reduction': max_improvement,
            'estimated_new_risk': potential_new_risk,
            'improvement_factors': improvement_factors,
            'confidence': "High" if max_improvement > 20 else "Medium" if max_improvement > 10 else "Moderate"
        }
    
    def _get_fallback_feedback(self, applicant_data: Dict, prediction_result: Dict) -> Dict:
        """Fallback feedback when AI services are unavailable"""
        return self._structure_feedback(
            self._get_rule_based_feedback(""),
            applicant_data,
            prediction_result
        )
