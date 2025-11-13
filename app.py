import streamlit as st
import json
import time
from datetime import datetime
from pinterest_scraper import validate_pinterest_url, MIN_REQUIRED_IMAGES
from apify_pinterest_scraper import extract_pinterest_board_images_apify, ApifyPinterestError
from ai_card_generator import generate_wedding_card_from_pinterest
from card_schema import validate_card_design
from card_renderer import render_card_design

st.set_page_config(
    page_title="Pinterest Wedding Card Generator",
    layout="wide"
)

def load_css():
    """Load custom CSS for kartenmacherei-inspired design"""
    try:
        with open('styles.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()

st.title("Pinterest-Powered Wedding Invitation Generator")
st.markdown("""
Transform your Pinterest wedding inspiration into a beautiful, personalized invitation design.
Simply paste your public Pinterest board URL and let AI create a unique design based on your aesthetic.
""")

if 'generated_design' not in st.session_state:
    st.session_state.generated_design = None
if 'pinterest_url' not in st.session_state:
    st.session_state.pinterest_url = ""
if 'generation_count' not in st.session_state:
    st.session_state.generation_count = 0


def progress_callback(message: str, current: int, total: int):
    """Callback for progress updates"""
    st.session_state.progress_message = message
    st.session_state.progress_value = current / total


col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Enter Your Pinterest Board")
    
    pinterest_url = st.text_input(
        "Pinterest Board URL",
        value=st.session_state.pinterest_url,
        placeholder="https://www.pinterest.com/yourname/your-board/",
        help="Paste the URL of your Pinterest wedding inspiration board"
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        generate_button = st.button("Generate Design", type="primary", use_container_width=True)
    
    with col_btn2:
        if st.session_state.generated_design:
            regenerate_button = st.button("Try Again", use_container_width=True)
        else:
            regenerate_button = False
    
    if generate_button or regenerate_button:
        # Validate Pinterest board URL
        if not pinterest_url:
            st.error("Please enter a Pinterest board URL")
            st.stop()
        elif not validate_pinterest_url(pinterest_url):
            st.error("Invalid URL format. Please enter a Pinterest board URL (e.g., https://pinterest.com/username/board-name/) — search results and individual pins are not supported.")
            st.stop()
        
        try:
            start_time = time.time()
            
            # Use Apify to scrape the board (reliable, handles JavaScript and bot detection)
            st.session_state.pinterest_url = pinterest_url
            with st.spinner("Fetching pins from Pinterest board via Apify..."):
                try:
                    image_urls = extract_pinterest_board_images_apify(pinterest_url, max_images=25)
                    
                    if not image_urls:
                        st.error(f"No pins found on this board. Please check the URL and ensure the board is public and contains images.")
                        st.stop()
                    elif len(image_urls) < MIN_REQUIRED_IMAGES:
                        st.error(f"Insufficient pins: Found only {len(image_urls)} pin(s). At least {MIN_REQUIRED_IMAGES} pins are required to create a meaningful design. Please use a board with more wedding inspiration images.")
                        st.stop()
                    elif len(image_urls) < 10:
                        st.warning(f"Found {len(image_urls)} pins. For best results, use a board with at least 10-15 pins.")
                        analyzed_count = len(image_urls)
                        st.info(f"Analyzing all {analyzed_count} available pins...")
                    else:
                        analyzed_count = min(10, len(image_urls))
                        st.success(f"Found {len(image_urls)} pins (analyzing top {analyzed_count} for optimal performance)")
                        
                except ApifyPinterestError as e:
                    st.error(f"{str(e)}")
                    st.stop()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(message, current, total):
                progress_value = min(1.0, max(0.0, current / total)) if total > 0 else 0.0
                progress_bar.progress(progress_value)
                status_text.text(message)
            
            with st.spinner("Analyzing your wedding aesthetic with AI..."):
                card_design = generate_wedding_card_from_pinterest(
                    image_urls,
                    progress_callback=update_progress
                )
            
            elapsed_time = time.time() - start_time
            
            try:
                validate_card_design(card_design)
                st.session_state.generated_design = card_design
                st.session_state.generation_count += 1
                
                progress_bar.empty()
                status_text.empty()
                
                st.success(f"Design generated successfully in {elapsed_time:.1f} seconds!")
                st.rerun()
                
            except Exception as validation_error:
                st.error(f"Generated design validation failed: {str(validation_error)}")
                
        except Exception as e:
            st.error(f"Error generating design: {str(e)}")
            import traceback
            with st.expander("Technical Details"):
                st.code(traceback.format_exc())

with col2:
    st.subheader("How It Works")
    st.markdown("""
    1. **Share Your Vision**: Paste your Pinterest board URL
    2. **AI Analysis**: Our AI analyzes colors, styles, and themes
    3. **Design Generation**: A unique invitation is created
    4. **Preview & Refine**: View your design and regenerate if desired
    
    **Tip**: Boards with 15-30 images work best!
    """)
    
    if st.session_state.generation_count > 0:
        st.metric("Designs Generated", st.session_state.generation_count)

if st.session_state.generated_design:
    st.divider()
    
    st.subheader("Your Generated Wedding Invitation")
    
    design = st.session_state.generated_design
    
    col_preview, col_details = st.columns([2, 1])
    
    with col_preview:
        st.markdown("### Preview")
        
        # Try to display AI-generated image first (preferred)
        generated_image_path = design.get('_generated_image_path')
        
        if generated_image_path:
            try:
                st.image(generated_image_path, caption="Your AI-Generated Wedding Invitation", use_container_width=True)
                st.success("Generated with Gemini 2.5 Flash Image (nano banana)")
            except Exception as e:
                st.error(f"Error displaying AI-generated image: {str(e)}")
                st.info("Falling back to structured preview...")
                generated_image_path = None
        
        # Fallback to PIL render or details if AI generation failed
        if not generated_image_path:
            if '_image_generation_error' in design:
                st.warning(f"AI image generation failed: {design['_image_generation_error']}")
            
            try:
                card_image = render_card_design(design, dpi=150)
                st.image(card_image, caption="Design Preview (PIL Renderer)", use_container_width=True)
                st.info("Note: This is a simplified preview. For Pinterest-quality designs, AI image generation is recommended.")
            except Exception as e:
                st.error(f"Error rendering preview: {str(e)}")
                st.info("Showing design details instead:")
                
                card_info = design.get('card', {})
                st.markdown(f"""
                **Background Color**: {card_info.get('backgroundColor', '#FFFFFF')}  
                **Dimensions**: {card_info.get('width', 148)}mm × {card_info.get('height', 105)}mm
                """)
    
    with col_details:
        st.markdown("### Design Details")
        
        card_info = design.get('card', {})
        st.markdown(f"""
        **Card Size**: {card_info.get('width', 148)}mm × {card_info.get('height', 105)}mm (A6)  
        **Background**: {card_info.get('backgroundColor', '#FFFFFF')}
        """)
        
        elements = design.get('elements', [])
        text_elements = [e for e in elements if e.get('type') == 'text']
        decorative_elements = [e for e in elements if e.get('type') == 'decorative']
        
        st.markdown(f"""
        **Text Elements**: {len(text_elements)}  
        **Decorative Elements**: {len(decorative_elements)}
        """)
        
        if '_source_images_count' in design:
            st.markdown(f"**Source Images Analyzed**: {design['_source_images_count']}")
        
        if '_design_brief' in design:
            with st.expander("View Design Brief"):
                st.markdown(design['_design_brief'])
        
        with st.expander("View JSON Output"):
            display_design = {k: v for k, v in design.items() if not k.startswith('_')}
            st.json(display_design)
        
        st.download_button(
            label="Download JSON",
            data=json.dumps(display_design, indent=2),
            file_name=f"wedding_card_design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

st.divider()

with st.expander("About This Prototype"):
    st.markdown("""
    ### Pinterest-Powered Wedding Invitation Generator (Prototype)
    
    This is an **AI Core Proof of Concept** for kartenmacherei.de that demonstrates:
    
    - **No Authentication Required**: Access any public Pinterest board instantly
    - **AI-Powered Design**: Multi-stage AI pipeline using Gemini vision models
    - **Structured Output**: Generate production-ready JSON design specifications
    - **Brand Alignment**: Designs follow kartenmacherei.de aesthetic standards
    
    #### Technology Stack
    - **Pinterest Scraping**: Apify professional scraping service (reliable, handles JavaScript)
    - **AI Analysis**: Google Gemini 2.5 Flash & Pro (multimodal vision)
    - **Design Schema**: Pydantic-validated JSON output
    - **Rendering**: PIL for visual preview generation
    
    #### Performance Metrics
    - **Target Generation Time**: < 30 seconds
    - **Success Rate Goal**: > 95%
    - **User Satisfaction Goal**: > 4.0/5.0
    
    *Next Phase: Integration with kartenmacherei.de configurator*
    """)

st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666;">Built for kartenmacherei.de | Powered by Replit AI Integrations</div>',
    unsafe_allow_html=True
)
