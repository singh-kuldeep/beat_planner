import json
import os
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from openai import OpenAI

class AITerritoryOptimizer:
    """
    AI-powered territory optimization using OpenAI GPT-4o for intelligent analysis
    and recommendations for improving sales territory efficiency.
    """
    
    def __init__(self):
        """Initialize the AI optimizer with OpenAI client."""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if self.api_key:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            self.client = OpenAI(api_key=self.api_key)
            self.model = "gpt-4o"
        else:
            self.client = None
            self.model = None
    
    def is_available(self) -> bool:
        """Check if AI optimization is available (API key provided)."""
        return self.client is not None
    
    def analyze_territory_efficiency(self, territories: List[Dict], merchant_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze current territory setup and provide efficiency metrics.
        
        Args:
            territories: List of territory dictionaries
            merchant_data: DataFrame with merchant information
            
        Returns:
            Dictionary with efficiency analysis
        """
        if not self.is_available():
            return {"error": "OpenAI API key not provided. AI optimization unavailable."}
        
        try:
            # Calculate basic statistics
            stats = self._calculate_territory_stats(territories, merchant_data)
            
            # Prepare data for AI analysis
            analysis_prompt = self._create_analysis_prompt(stats, territories, merchant_data)
            
            # Get AI analysis
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sales territory optimization consultant. "
                        "Analyze territory data and provide actionable insights for improving "
                        "efficiency, coverage, and workload balance. Respond with structured JSON."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            analysis = json.loads(response.choices[0].message.content)
            analysis.update(stats)
            
            return analysis
            
        except Exception as e:
            return {"error": f"AI analysis failed: {str(e)}"}
    
    def get_optimization_suggestions(self, territories: List[Dict], merchant_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get AI-powered optimization suggestions for territories.
        
        Args:
            territories: List of territory dictionaries
            merchant_data: DataFrame with merchant information
            
        Returns:
            Dictionary with optimization suggestions
        """
        if not self.is_available():
            return {
                "error": "OpenAI API key not provided. Please provide your OpenAI API key to enable AI-powered optimization suggestions.",
                "suggestions": [
                    {
                        "type": "manual",
                        "priority": "high",
                        "title": "Enable AI Optimization",
                        "description": "Provide OpenAI API key to unlock intelligent territory optimization suggestions",
                        "action": "Add OPENAI_API_KEY to enable AI-powered analysis"
                    }
                ]
            }
        
        try:
            # Get efficiency analysis first
            analysis = self.analyze_territory_efficiency(territories, merchant_data)
            
            if "error" in analysis:
                return analysis
            
            # Create optimization prompt
            optimization_prompt = self._create_optimization_prompt(analysis, territories, merchant_data)
            
            # Get AI suggestions
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert sales territory optimization consultant. "
                        "Provide specific, actionable optimization suggestions based on the "
                        "territory analysis. Focus on practical improvements for coverage, "
                        "efficiency, and workload balance. Respond with structured JSON containing "
                        "prioritized suggestions with specific actions."
                    },
                    {
                        "role": "user",
                        "content": optimization_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            
            suggestions = json.loads(response.choices[0].message.content)
            
            return suggestions
            
        except Exception as e:
            return {"error": f"AI optimization failed: {str(e)}"}
    
    def _calculate_territory_stats(self, territories: List[Dict], merchant_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic territory statistics for AI analysis."""
        total_merchants = len(merchant_data)
        
        # Assigned vs unassigned merchants
        assigned_merchants = set()
        for territory in territories:
            assigned_merchants.update(territory.get('merchants', []))
        
        assigned_count = len(assigned_merchants)
        unassigned_count = total_merchants - assigned_count
        
        # Territory size distribution
        territory_sizes = [len(territory.get('merchants', [])) for territory in territories]
        
        # Executive workload distribution
        executive_workloads = {}
        for territory in territories:
            exec_name = territory.get('executive', 'Unknown')
            if exec_name not in executive_workloads:
                executive_workloads[exec_name] = 0
            executive_workloads[exec_name] += len(territory.get('merchants', []))
        
        # Geographic spread analysis
        territory_radii = [territory.get('radius', 0) / 1000 for territory in territories]  # Convert to km
        
        return {
            "total_merchants": total_merchants,
            "total_territories": len(territories),
            "assigned_merchants": assigned_count,
            "unassigned_merchants": unassigned_count,
            "assignment_percentage": (assigned_count / total_merchants * 100) if total_merchants > 0 else 0,
            "territory_sizes": territory_sizes,
            "avg_territory_size": np.mean(territory_sizes) if territory_sizes else 0,
            "min_territory_size": min(territory_sizes) if territory_sizes else 0,
            "max_territory_size": max(territory_sizes) if territory_sizes else 0,
            "territory_size_std": np.std(territory_sizes) if territory_sizes else 0,
            "executive_workloads": executive_workloads,
            "territory_radii": territory_radii,
            "avg_territory_radius": np.mean(territory_radii) if territory_radii else 0,
            "total_executives": len(executive_workloads)
        }
    
    def _create_analysis_prompt(self, stats: Dict, territories: List[Dict], merchant_data: pd.DataFrame) -> str:
        """Create analysis prompt for AI."""
        return f"""
        Analyze this sales territory configuration:
        
        TERRITORY STATISTICS:
        - Total merchants: {stats['total_merchants']}
        - Total territories: {stats['total_territories']}
        - Assigned merchants: {stats['assigned_merchants']} ({stats['assignment_percentage']:.1f}%)
        - Unassigned merchants: {stats['unassigned_merchants']}
        - Average territory size: {stats['avg_territory_size']:.1f} merchants
        - Territory size range: {stats['min_territory_size']}-{stats['max_territory_size']} merchants
        - Territory size variation (std dev): {stats['territory_size_std']:.1f}
        - Average territory radius: {stats['avg_territory_radius']:.1f} km
        - Number of executives: {stats['total_executives']}
        
        EXECUTIVE WORKLOADS:
        {json.dumps(stats['executive_workloads'], indent=2)}
        
        TERRITORY SIZES: {stats['territory_sizes']}
        TERRITORY RADII (km): {stats['territory_radii']}
        
        Provide analysis in JSON format with these keys:
        - efficiency_score: Overall efficiency rating (0-100)
        - balance_score: Workload balance rating (0-100)
        - coverage_score: Geographic coverage rating (0-100)
        - key_insights: List of 3-5 main observations
        - strengths: List of current strengths
        - weaknesses: List of areas needing improvement
        """
    
    def _create_optimization_prompt(self, analysis: Dict, territories: List[Dict], merchant_data: pd.DataFrame) -> str:
        """Create optimization prompt for AI suggestions."""
        return f"""
        Based on this territory analysis, provide optimization suggestions:
        
        CURRENT PERFORMANCE:
        - Efficiency Score: {analysis.get('efficiency_score', 'N/A')}
        - Balance Score: {analysis.get('balance_score', 'N/A')}
        - Coverage Score: {analysis.get('coverage_score', 'N/A')}
        
        KEY INSIGHTS: {json.dumps(analysis.get('key_insights', []), indent=2)}
        WEAKNESSES: {json.dumps(analysis.get('weaknesses', []), indent=2)}
        
        TERRITORY STATISTICS:
        - {analysis['unassigned_merchants']} unassigned merchants
        - Territory size variation: {analysis['territory_size_std']:.1f}
        - Average radius: {analysis['avg_territory_radius']:.1f} km
        - Executive workloads: {json.dumps(analysis['executive_workloads'], indent=2)}
        
        Provide optimization suggestions in JSON format with:
        - suggestions: Array of suggestion objects with:
          - type: "rebalance" | "merge" | "split" | "reassign" | "coverage"
          - priority: "high" | "medium" | "low"
          - title: Brief title
          - description: Detailed explanation
          - action: Specific action to take
          - expected_improvement: Expected benefit
        - overall_strategy: High-level optimization strategy
        - implementation_order: Recommended order of implementation
        """