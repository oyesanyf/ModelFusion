#!/usr/bin/env python3
"""
PE Analysis with AI-Powered Malware Detection
Comprehensive PE file analysis using the best HuggingFace malware detection models
"""

import os
import sys
import asyncio
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import our custom modules
from enhanced_pe_analyzer import EnhancedPEAnalyzer
from find_best_malware_models import MalwareModelFinder

class PEAnalysisWithAI:
    """Comprehensive PE analysis with AI-powered malware detection"""
    
    def __init__(self, hf_token: Optional[str] = None):
        self.hf_token = hf_token or os.getenv('HF_TOKEN')
        self.pe_analyzer = EnhancedPEAnalyzer(hf_token=self.hf_token)
        self.model_finder = MalwareModelFinder()
        
    async def analyze_file(self, file_path: str, output_dir: str = "reports") -> Dict:
        """Analyze a PE file comprehensively with AI models"""
        print(f"🔍 Starting comprehensive analysis of: {file_path}")
        print("=" * 60)
        
        # Step 1: Find best malware detection models
        print("📊 Step 1: Finding best malware detection models...")
        best_models = self.model_finder.get_recommended_models_for_pe_analysis()
        
        if best_models:
            print(f"✅ Found {len(best_models)} recommended models")
            for i, model in enumerate(best_models[:3], 1):
                print(f"   {i}. {model['model_id']} (Score: {model.get('quality_score', 'N/A'):.1f})")
        else:
            print("⚠️  Using fallback models")
        
        # Step 2: Perform static PE analysis
        print("\n🔍 Step 2: Performing static PE analysis...")
        static_analysis = self.pe_analyzer.analyze_pe_file(file_path)
        
        if 'error' in static_analysis:
            print(f"❌ Static analysis failed: {static_analysis['error']}")
            return static_analysis
        
        print(f"✅ Static analysis completed. Verdict: {static_analysis.get('verdict', 'UNKNOWN')}")
        
        # Step 3: AI-powered analysis (if models available)
        ai_analysis = {}
        if best_models and self.pe_analyzer.hf_orchestrator:
            print("\n🤖 Step 3: Performing AI-powered analysis...")
            try:
                ai_analysis = await self.pe_analyzer.analyze_with_ai_models(static_analysis)
                if 'error' not in ai_analysis:
                    print(f"✅ AI analysis completed with {len(ai_analysis)} models")
                else:
                    print(f"⚠️  AI analysis failed: {ai_analysis['error']}")
            except Exception as e:
                print(f"❌ AI analysis error: {e}")
                ai_analysis = {'error': str(e)}
        
        # Step 4: Combine results
        print("\n📋 Step 4: Combining analysis results...")
        combined_analysis = {
            **static_analysis,
            'ai_analysis': ai_analysis,
            'best_models': best_models[:5],  # Top 5 models
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_type': 'comprehensive_with_ai'
        }
        
        # Step 5: Determine final verdict
        final_verdict = self._determine_final_verdict(combined_analysis)
        combined_analysis['final_verdict'] = final_verdict
        
        print(f"✅ Final verdict: {final_verdict}")
        
        return combined_analysis
    
    def _determine_final_verdict(self, analysis: Dict) -> str:
        """Determine final verdict combining static and AI analysis"""
        static_verdict = analysis.get('verdict', 'UNKNOWN')
        ai_analysis = analysis.get('ai_analysis', {})
        
        # If OTX says malicious, that takes precedence
        if analysis.get('otx', {}).get('otx_malicious', False):
            return "MALICIOUS"
        
        # Check AI model results
        ai_malicious_count = 0
        ai_total_count = 0
        
        for model_id, result in ai_analysis.items():
            if isinstance(result, dict) and 'error' not in result:
                ai_total_count += 1
                confidence = result.get('confidence', 0.5)
                # Consider high confidence results
                if confidence > 0.7:
                    ai_malicious_count += 1
        
        # If majority of AI models say malicious
        if ai_total_count > 0 and ai_malicious_count / ai_total_count > 0.6:
            return "MALICIOUS"
        
        # Otherwise, trust static analysis
        return static_verdict
    
    def print_comprehensive_summary(self, analysis: Dict):
        """Print a comprehensive summary of the analysis"""
        print("\n" + "="*80)
        print("🔍 COMPREHENSIVE PE ANALYSIS SUMMARY")
        print("="*80)
        
        # Basic file info
        print(f"📁 File: {analysis.get('file_name', 'Unknown')}")
        print(f"📏 Size: {analysis.get('file_size', 0):,} bytes")
        print(f"🔐 Static Verdict: {analysis.get('verdict', 'UNKNOWN')}")
        print(f"🎯 Final Verdict: {analysis.get('final_verdict', 'UNKNOWN')}")
        
        # Hashes
        hashes = analysis.get('hashes', {})
        if hashes:
            print(f"🔗 SHA256: {hashes.get('sha256', 'N/A')}")
        
        # Strong indicators
        strong = analysis.get('strong_indicators', [])
        if strong:
            print(f"\n🚨 Strong Indicators ({len(strong)}):")
            for indicator in strong:
                print(f"  • {indicator}")
        
        # Weak indicators
        weak = analysis.get('weak_indicators', [])
        if weak:
            print(f"\n⚠️  Weak Indicators ({len(weak)}):")
            for indicator in weak[:5]:  # Show first 5
                print(f"  • {indicator}")
            if len(weak) > 5:
                print(f"  ... and {len(weak) - 5} more")
        
        # OTX results
        otx = analysis.get('otx', {})
        if otx and not otx.get('error'):
            print(f"\n🌐 OTX Intelligence:")
            print(f"  • Malicious: {otx.get('otx_malicious', False)}")
            print(f"  • Positives: {otx.get('otx_positives', 0)}")
            if otx.get('otx_pulses'):
                print(f"  • Pulses: {', '.join(otx['otx_pulses'][:3])}")
        
        # AI analysis results
        ai_analysis = analysis.get('ai_analysis', {})
        if ai_analysis and 'error' not in ai_analysis:
            print(f"\n🤖 AI Model Analysis:")
            for model_id, result in ai_analysis.items():
                if isinstance(result, dict) and 'error' not in result:
                    confidence = result.get('confidence', 0.5)
                    print(f"  • {model_id}: {confidence:.2f} confidence")
        
        # Best models used
        best_models = analysis.get('best_models', [])
        if best_models:
            print(f"\n🏆 Best Models Used:")
            for i, model in enumerate(best_models[:3], 1):
                print(f"  {i}. {model['model_id']} (Score: {model.get('quality_score', 'N/A'):.1f})")
        
        print("="*80)
    
    def save_analysis(self, analysis: Dict, output_path: str):
        """Save comprehensive analysis results"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Comprehensive analysis saved to: {output_path}")
            
        except Exception as e:
            print(f"❌ Failed to save analysis: {e}")
    
    def generate_security_report(self, analysis: Dict) -> str:
        """Generate a human-readable security report"""
        report = []
        report.append("="*80)
        report.append("🔒 PE FILE SECURITY ANALYSIS REPORT")
        report.append("="*80)
        report.append("")
        
        # Executive Summary
        report.append("📋 EXECUTIVE SUMMARY")
        report.append("-" * 40)
        report.append(f"File: {analysis.get('file_name', 'Unknown')}")
        report.append(f"Size: {analysis.get('file_size', 0):,} bytes")
        report.append(f"Final Verdict: {analysis.get('final_verdict', 'UNKNOWN')}")
        report.append(f"Analysis Date: {analysis.get('analysis_timestamp', 'Unknown')}")
        report.append("")
        
        # Threat Assessment
        report.append("🚨 THREAT ASSESSMENT")
        report.append("-" * 40)
        
        strong_count = len(analysis.get('strong_indicators', []))
        weak_count = len(analysis.get('weak_indicators', []))
        
        if analysis.get('final_verdict') == 'MALICIOUS':
            report.append("❌ HIGH RISK - File appears to be malicious")
            report.append("   • Multiple strong indicators detected")
            report.append("   • Recommend immediate quarantine")
        elif analysis.get('final_verdict') == 'SUSPICIOUS':
            report.append("⚠️  MEDIUM RISK - File shows suspicious behavior")
            report.append("   • Some concerning indicators present")
            report.append("   • Recommend further analysis in sandbox")
        else:
            report.append("✅ LOW RISK - File appears to be clean")
            report.append("   • No strong malicious indicators detected")
            report.append("   • Standard security practices recommended")
        
        report.append("")
        
        # Detailed Findings
        report.append("🔍 DETAILED FINDINGS")
        report.append("-" * 40)
        
        # Strong indicators
        strong = analysis.get('strong_indicators', [])
        if strong:
            report.append(f"Strong Indicators ({len(strong)}):")
            for indicator in strong:
                report.append(f"  • {indicator}")
            report.append("")
        
        # Weak indicators
        weak = analysis.get('weak_indicators', [])
        if weak:
            report.append(f"Weak Indicators ({len(weak)}):")
            for indicator in weak[:10]:  # Limit to first 10
                report.append(f"  • {indicator}")
            if len(weak) > 10:
                report.append(f"  ... and {len(weak) - 10} more")
            report.append("")
        
        # OTX Intelligence
        otx = analysis.get('otx', {})
        if otx and not otx.get('error'):
            report.append("🌐 THREAT INTELLIGENCE (OTX)")
            report.append("-" * 40)
            report.append(f"Known Malicious: {otx.get('otx_malicious', False)}")
            report.append(f"Positive Detections: {otx.get('otx_positives', 0)}")
            if otx.get('otx_pulses'):
                report.append("Related Threat Campaigns:")
                for pulse in otx['otx_pulses'][:5]:
                    report.append(f"  • {pulse}")
            report.append("")
        
        # AI Analysis Results
        ai_analysis = analysis.get('ai_analysis', {})
        if ai_analysis and 'error' not in ai_analysis:
            report.append("🤖 AI MODEL ANALYSIS")
            report.append("-" * 40)
            for model_id, result in ai_analysis.items():
                if isinstance(result, dict) and 'error' not in result:
                    confidence = result.get('confidence', 0.5)
                    report.append(f"{model_id}: {confidence:.2f} confidence")
            report.append("")
        
        # Recommendations
        report.append("💡 SECURITY RECOMMENDATIONS")
        report.append("-" * 40)
        
        verdict = analysis.get('final_verdict', 'UNKNOWN')
        if verdict == 'MALICIOUS':
            report.append("• IMMEDIATE ACTION REQUIRED:")
            report.append("  - Quarantine the file immediately")
            report.append("  - Scan all systems for similar files")
            report.append("  - Review system logs for suspicious activity")
            report.append("  - Consider full system scan")
        elif verdict == 'SUSPICIOUS':
            report.append("• CAUTION RECOMMENDED:")
            report.append("  - Analyze in isolated sandbox environment")
            report.append("  - Monitor system behavior if executed")
            report.append("  - Verify file source and authenticity")
            report.append("  - Consider additional security tools")
        else:
            report.append("• STANDARD SECURITY PRACTICES:")
            report.append("  - Keep antivirus software updated")
            report.append("  - Verify file source before execution")
            report.append("  - Use standard security monitoring")
            report.append("  - Regular system scans recommended")
        
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='PE Analysis with AI-Powered Malware Detection')
    parser.add_argument('file_path', help='Path to the PE file to analyze')
    parser.add_argument('--output-dir', default='reports', help='Output directory for reports')
    parser.add_argument('--hf-token', help='HuggingFace API token')
    parser.add_argument('--save-report', action='store_true', help='Save human-readable report')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        print(f"❌ Error: File not found: {args.file_path}")
        sys.exit(1)
    
    # Initialize analyzer
    analyzer = PEAnalysisWithAI(hf_token=args.hf_token)
    
    # Run analysis
    analysis = await analyzer.analyze_file(args.file_path, args.output_dir)
    
    if 'error' in analysis:
        print(f"❌ Analysis failed: {analysis['error']}")
        sys.exit(1)
    
    # Print summary
    analyzer.print_comprehensive_summary(analysis)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(args.file_path).stem
    
    # Save JSON analysis
    json_path = os.path.join(args.output_dir, f"{base_name}_comprehensive_analysis_{timestamp}.json")
    analyzer.save_analysis(analysis, json_path)
    
    # Save human-readable report
    if args.save_report:
        report_text = analyzer.generate_security_report(analysis)
        report_path = os.path.join(args.output_dir, f"{base_name}_security_report_{timestamp}.txt")
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"📄 Security report saved to: {report_path}")
        except Exception as e:
            print(f"❌ Failed to save security report: {e}")
    
    print(f"\n✅ Analysis completed successfully!")
    print(f"📁 Results saved to: {args.output_dir}")

if __name__ == "__main__":
    asyncio.run(main()) 