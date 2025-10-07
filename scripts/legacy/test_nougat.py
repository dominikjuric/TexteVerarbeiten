#!/usr/bin/env python3
"""
Quick test script for Nougat processor
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from formulas.nougat_processor import create_nougat_processor

def main():
    # Find a smaller math PDF from available files
    math_pdfs = [
        Path('raw/Leonid Berlyand, Pierre-Emmanuel Jabin - Mathematics of Deep Learning. An Introduction (2023, DE GRUYTER) - libgen.li.pdf'),
        Path('raw/Philipp Grohs (editor), Gitta Kutyniok (editor) - Mathematical Aspects of Deep Learning (2023, Cambridge University Press) - libgen.li.pdf'),
        # Use a smaller/simpler PDF for testing  
        Path('raw/Numerische Strömungsmechanik by Eckart Laurien, Herbert Oertel jr. (z-lib.org).pdf')
    ]

    for pdf in math_pdfs:
        if pdf.exists():
            print(f'🧪 Testing Nougat with: {pdf.name[:50]}...')
            
            processor = create_nougat_processor()
            if processor:
                print("✅ Nougat processor created")
                print(f"📊 Model: {processor.get_model_info()}")
                print(f"🚀 Starting processing...")
                
                # Process PDF
                result = processor.process_pdf(pdf)
                
                if result['success']:
                    print(f"✅ Success! Processing time: {result['processing_time']:.1f}s")
                    print(f"💾 Output: {result['output_path']}")
                    print(f"📝 Content length: {len(result['markdown'])} characters")
                    
                    # Show preview
                    lines = result['markdown'].split('\n')[:3]
                    print("📖 Preview:")
                    for line in lines:
                        print(f"   {line}")
                else:
                    print(f"❌ Failed: {result['error']}")
                    
                break
            else:
                print('❌ Could not create Nougat processor')
                break
    else:
        print('❌ No suitable test PDF found')
        print('📁 Available PDFs:')
        for pdf in Path('raw').glob('*.pdf'):
            print(f'   {pdf.name}')

if __name__ == "__main__":
    main()