import streamlit as st
import json
import os
from datetime import datetime
import random

# ============================================================================
# CONFIGURATION
# ============================================================================

# Set to False to hide PBQ Builder and Question Bank (public deployment mode)
SHOW_BUILDER = False

# Page configuration
st.set_page_config(
    page_title="PBQ Time",
    page_icon="👺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for input field width
st.markdown("""
<style>
    /* Limit selectbox width in practice mode */
    div[data-testid="stSelectbox"] {
        max-width: 500px !important;
    }
    
    /* Limit text input width */
    div[data-testid="stTextInput"] {
        max-width: 600px !important;
    }
    
    /* Limit text area width */
    div[data-testid="stTextArea"] {
        max-width: 800px !important;
    }
    
    /* File uploader width */
    div[data-testid="stFileUploader"] {
        max-width: 600px !important;
    }
    
    /* Number input width */
    div[data-testid="stNumberInput"] {
        max-width: 300px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA PERSISTENCE FUNCTIONS
# ============================================================================

def save_question_bank():
    """Save question bank to JSON file"""
    try:
        os.makedirs('data', exist_ok=True)
        
        if not st.session_state.question_bank:
            with open('data/question_bank.json', 'w', encoding='utf-8') as f:
                f.write('[]')
            return True
        
        # Clean data for serialization
        question_bank_clean = []
        for question in st.session_state.question_bank:
            question_clean = question.copy()
            
            # Remove binary data
            if 'scenario_image' in question_clean:
                del question_clean['scenario_image']
            
            if 'pbq_data' in question_clean:
                pbq_data_clean = question_clean['pbq_data'].copy()
                if 'scenario_image' in pbq_data_clean:
                    del pbq_data_clean['scenario_image']
                question_clean['pbq_data'] = pbq_data_clean
            
            question_bank_clean.append(question_clean)
        
        with open('data/question_bank.json', 'w', encoding='utf-8') as f:
            json.dump(question_bank_clean, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"Error saving question bank: {e}")
        return False

def load_question_bank():
    """Load question bank from JSON file"""
    try:
        file_path = 'data/question_bank.json'
        
        if not os.path.exists(file_path):
            return []
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            if not content:
                return []
            
            data = json.loads(content)
            return data if isinstance(data, list) else []
                    
    except Exception:
        return []

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize all session state variables"""
    
    if 'question_bank' not in st.session_state:
        st.session_state.question_bank = load_question_bank()
    
    session_vars = {
        'current_page': "Practice Mode",
        'current_question_index': 0,
        'user_answers': {},
        'practice_started': False,
        'selected_questions': [],
        'session_results': {},
        'show_answers': False,
        'shuffle_questions': False,
        'shuffle_options': False,
        'real_time_score': {
            'correct': 0, 'incorrect': 0, 'unanswered': 0,
            'current_streak': 0, 'best_streak': 0,
            'total_answered': 0, 'accuracy': 0
        },
        'detailed_results': []
    }
    
    for var_name, default_value in session_vars.items():
        if var_name not in st.session_state:
            st.session_state[var_name] = default_value

# ============================================================================
# PRACTICE MODE FUNCTIONS
# ============================================================================

def start_practice_session():
    """Initialize a new practice session"""
    st.session_state.practice_started = True
    st.session_state.current_question_index = 0
    st.session_state.user_answers = {}
    st.session_state.session_results = {}
    st.session_state.show_answers = False
    st.session_state.detailed_results = []
    
    if not st.session_state.selected_questions:
        total_questions = len(st.session_state.question_bank)
        if total_questions > 0:
            question_count = min(10, total_questions)
            st.session_state.selected_questions = st.session_state.question_bank[:question_count]
    
    # Shuffle questions if enabled
    if st.session_state.shuffle_questions:
        random.shuffle(st.session_state.selected_questions)
    
    for i in range(len(st.session_state.selected_questions)):
        if i not in st.session_state.user_answers:
            st.session_state.user_answers[i] = {}
    
    st.rerun()

def end_practice_session():
    """End the current practice session and show results"""
    st.session_state.practice_started = False
    st.session_state.show_answers = True
    calculate_detailed_results()
    st.rerun()

def calculate_real_time_score():
    """Calculate real-time scoring metrics with partial credit for PBQs"""
    if not st.session_state.selected_questions:
        return
    
    correct = 0
    incorrect = 0
    unanswered = 0
    current_streak = 0
    best_streak = 0
    
    for i in range(len(st.session_state.selected_questions)):
        question = st.session_state.selected_questions[i]
        user_answer = st.session_state.user_answers.get(i)
        
        if question.get('is_pbq'):
            if user_answer and isinstance(user_answer, dict) and user_answer:
                try:
                    correct_answers_raw = question.get('correct_answer', '{}')
                    
                    if isinstance(correct_answers_raw, str):
                        correct_answers = json.loads(correct_answers_raw)
                    else:
                        correct_answers = correct_answers_raw
                    
                    correct_items = 0
                    total_items = len(correct_answers)
                    
                    if total_items > 0:
                        for item_key, correct_value in correct_answers.items():
                            user_value = user_answer.get(item_key)
                            if user_value == correct_value:
                                correct_items += 1
                        
                        accuracy = correct_items / total_items
                        
                        if accuracy >= 0.5:
                            correct += 1
                            current_streak += 1
                            best_streak = max(best_streak, current_streak)
                        else:
                            incorrect += 1
                            current_streak = 0
                    else:
                        unanswered += 1
                        current_streak = 0
                        
                except Exception:
                    incorrect += 1
                    current_streak = 0
            else:
                unanswered += 1
                current_streak = 0
        else:
            correct_answer = question.get('correct_answer')
            
            if user_answer is None:
                unanswered += 1
                current_streak = 0
            elif user_answer == correct_answer:
                correct += 1
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                incorrect += 1
                current_streak = 0
    
    total_answered = correct + incorrect
    
    st.session_state.real_time_score = {
        'correct': correct,
        'incorrect': incorrect,
        'unanswered': unanswered,
        'current_streak': current_streak,
        'best_streak': best_streak,
        'total_answered': total_answered,
        'accuracy': (correct / total_answered) * 100 if total_answered > 0 else 0
    }

def calculate_detailed_results():
    """Calculate detailed results for each question with item-by-item breakdown"""
    st.session_state.detailed_results = []
    correct_count = 0
    incorrect_count = 0
    total_questions = len(st.session_state.selected_questions)
    
    for i, question in enumerate(st.session_state.selected_questions):
        user_answer = st.session_state.user_answers.get(i)
        correct_answer_raw = question.get('correct_answer')
        pbq_type = question.get('type', '').replace('PBQ - ', '')
        
        result = {
            'question_num': i + 1,
            'question_type': pbq_type,
            'instructions': question.get('pbq_data', {}).get('instructions', ''),
            'items': []
        }
        
        question_is_correct = False
        
        if question.get('is_pbq'):
            try:
                if isinstance(correct_answer_raw, str):
                    correct_answers = json.loads(correct_answer_raw) if correct_answer_raw else {}
                else:
                    correct_answers = correct_answer_raw or {}
                
                if pbq_type == "Classification/Matching":
                    # Classification scoring
                    matching_items = question.get('pbq_data', {}).get('matching_items', [])
                    is_multi_select = question.get('pbq_data', {}).get('is_multi_select', False)
                    correct_items = 0
                    
                    for idx, item_text in enumerate(matching_items):
                        user_val = user_answer.get(str(idx), [] if is_multi_select else "") if user_answer else ([] if is_multi_select else "")
                        correct_val = correct_answers.get(str(idx), [] if is_multi_select else "")
                        
                        # Handle multi-select comparison
                        if is_multi_select:
                            if not isinstance(user_val, list):
                                user_val = [user_val] if user_val else []
                            if not isinstance(correct_val, list):
                                correct_val = [correct_val] if correct_val else []
                            is_correct = set(user_val) == set(correct_val)
                        else:
                            is_correct = user_val == correct_val
                        
                        if is_correct:
                            correct_items += 1
                        
                        result['items'].append({
                            'number': idx + 1,
                            'description': item_text,
                            'user_answer': user_val,
                            'correct_answer': correct_val,
                            'is_correct': is_correct,
                            'is_multi_select': is_multi_select
                        })
                    
                    result['score'] = correct_items
                    result['total'] = len(matching_items)
                    
                    # Question counts as correct if >= 50% correct
                    if correct_items / len(matching_items) >= 0.5:
                        correct_count += 1
                        question_is_correct = True
                    else:
                        incorrect_count += 1
                
                elif pbq_type == "Firewall Rules":
                    # Firewall scoring (per row)
                    firewall_rules = question.get('pbq_data', {}).get('firewall_rules', [])
                    correct_rows = 0
                    total_fields = 0
                    correct_fields = 0
                    
                    for rule_idx, rule in enumerate(firewall_rules):
                        fields = ['rule', 'source_ip', 'dest_ip', 'protocol', 'port', 'action']
                        row_correct = 0
                        row_total = len(fields)
                        total_fields += row_total
                        
                        row_result = {
                            'rule_number': rule_idx + 1,
                            'fields': [],
                            'user_row': {},
                            'correct_row': {}
                        }
                        
                        for field in fields:
                            user_val = user_answer.get(f"{rule_idx}_{field}", "") if user_answer else ""
                            correct_val = correct_answers.get(f"{rule_idx}_{field}", "")
                            is_correct = user_val == correct_val
                            
                            if is_correct:
                                row_correct += 1
                                correct_fields += 1
                            
                            row_result['fields'].append({
                                'name': field.replace('_', ' ').title(),
                                'user_value': user_val,
                                'correct_value': correct_val,
                                'is_correct': is_correct
                            })
                            
                            row_result['user_row'][field] = user_val
                            row_result['correct_row'][field] = correct_val
                        
                        row_result['row_score'] = row_correct
                        row_result['row_total'] = row_total
                        
                        if row_correct == row_total:
                            correct_rows += 1
                        
                        result['items'].append(row_result)
                    
                    result['score'] = correct_fields
                    result['total'] = total_fields
                    result['rows_correct'] = correct_rows
                    result['rows_total'] = len(firewall_rules)
                    
                    # Question counts as correct if >= 50% of fields correct
                    if correct_fields / total_fields >= 0.5:
                        correct_count += 1
                        question_is_correct = True
                    else:
                        incorrect_count += 1
                
            except Exception as e:
                result['error'] = str(e)
                incorrect_count += 1
        
        result['is_correct'] = question_is_correct
        st.session_state.detailed_results.append(result)
    
    # Update real-time score with correct counts
    st.session_state.real_time_score['correct'] = correct_count
    st.session_state.real_time_score['incorrect'] = incorrect_count
    st.session_state.real_time_score['total_answered'] = total_questions
    st.session_state.real_time_score['accuracy'] = (correct_count / total_questions) * 100 if total_questions > 0 else 0

# ============================================================================
# PRACTICE MODE UI
# ============================================================================

def render_practice_mode():
    """Render the practice mode interface"""
    st.header("🎯 Practice Mode")
    
    if not st.session_state.question_bank:
        st.warning("⚠️ No questions available. Please add questions first.")
        return
    
    if not st.session_state.practice_started:
        render_practice_settings()
    
    st.markdown("---")
    render_practice_controls()
    
    if st.session_state.practice_started and st.session_state.selected_questions:
        display_current_question()
    elif st.session_state.show_answers:
        display_session_summary()

def render_practice_settings():
    """Render practice session settings"""
    st.subheader("⚙️ Practice Session Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_questions = len(st.session_state.question_bank)
        
        if total_questions == 0:
            st.warning("No questions available")
            st.session_state.selected_questions = []
        elif total_questions == 1:
            st.session_state.selected_questions = st.session_state.question_bank
            st.info("1 question selected")
        else:
            question_count = st.slider(
                "Number of Questions",
                min_value=1,
                max_value=total_questions,
                value=min(10, total_questions),
                key="question_count_slider"
            )
            st.session_state.selected_questions = st.session_state.question_bank[:question_count]
    
    with col2:
        st.markdown("**Options:**")
        st.session_state.shuffle_questions = st.checkbox(
            "🔀 Shuffle Questions",
            value=st.session_state.shuffle_questions,
            key="shuffle_q"
        )
        st.session_state.shuffle_options = st.checkbox(
            "🔀 Shuffle Options (per PBQ)",
            value=st.session_state.shuffle_options,
            key="shuffle_o"
        )

def render_practice_controls():
    """Render practice session control buttons"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if not st.session_state.practice_started:
            if st.button("▶️ Start Practice", type="primary", key="start_btn", use_container_width=True):
                start_practice_session()
        else:
            if st.button("⏹️ End Practice", type="secondary", key="end_btn", use_container_width=True):
                end_practice_session()
    
    with col2:
        if st.session_state.practice_started:
            progress = (st.session_state.current_question_index + 1) / len(st.session_state.selected_questions)
            st.progress(progress)
            st.caption(f"Question {st.session_state.current_question_index + 1} of {len(st.session_state.selected_questions)}")
    
    with col3:
        if st.session_state.practice_started:
            score = st.session_state.real_time_score
            st.metric("Accuracy", f"{score['accuracy']:.0f}%")

def display_current_question():
    """Display the current question"""
    if st.session_state.current_question_index < len(st.session_state.selected_questions):
        question = st.session_state.selected_questions[st.session_state.current_question_index]
        
        if question.get('is_pbq'):
            display_pbq_question(question)
        else:
            display_regular_question(question)

def display_regular_question(question):
    """Display a regular multiple choice question"""
    current_index = st.session_state.current_question_index
    
    st.subheader(f"Question {current_index + 1}")
    
    if question.get('scenario'):
        with st.container():
            st.info(f"📋 Scenario: {question['scenario']}")
    
    st.markdown(f"**{question['question']}**")
    
    user_answer = st.session_state.user_answers.get(current_index)
    
    answer = st.radio(
        "Select your answer:",
        question['options'],
        index=question['options'].index(user_answer) if user_answer in question['options'] else None,
        key=f"regular_q_{current_index}"
    )
    
    if answer != user_answer:
        st.session_state.user_answers[current_index] = answer
        calculate_real_time_score()
        st.rerun()
    
    render_question_navigation()

def display_pbq_question(question):
    """Display PBQ question"""
    pbq_type = question.get('type', '').replace('PBQ - ', '')
    
    st.subheader("🎯 Performance-Based Question")
    st.caption(f"Type: {pbq_type}")
    
    if pbq_type == "Classification/Matching":
        display_matching_pbq(question)
    elif pbq_type == "Firewall Rules":
        display_firewall_pbq(question)

def display_matching_pbq(question):
    """Display matching PBQ"""
    pbq_data = question.get('pbq_data', {})
    current_index = st.session_state.current_question_index
    is_multi_select = pbq_data.get('is_multi_select', False)
    
    # Display scenario image if available
    image_filename = question.get('scenario_image_filename')
    if image_filename:
        try:
            image_path = os.path.join('data/images', image_filename)
            if os.path.exists(image_path):
                st.image(image_path, caption="Scenario", use_container_width=True)
        except Exception:
            pass
    
    with st.container():
        st.info(f"📋 {pbq_data.get('instructions', 'Match the items below')}")
    
    # Initialize user answers
    if current_index not in st.session_state.user_answers:
        st.session_state.user_answers[current_index] = {}
    
    user_answers = st.session_state.user_answers[current_index]
    matching_items = pbq_data.get('matching_items', [])
    all_options = pbq_data.get('all_options', [])
    
    # Shuffle options if enabled
    if st.session_state.shuffle_options:
        if f"shuffled_options_{current_index}" not in st.session_state:
            st.session_state[f"shuffled_options_{current_index}"] = random.sample(all_options, len(all_options))
        display_options = st.session_state[f"shuffled_options_{current_index}"]
    else:
        display_options = all_options
    
    answer_changed = False
    
    st.markdown("### Items to Match")
    
    if is_multi_select:
        st.caption("💡 Select all that apply for each item")
    
    for i, item in enumerate(matching_items):
        with st.container():
            st.markdown(f"**{i+1}.** {item}")
            
            if is_multi_select:
                # Multi-select with checkboxes
                current_answers = user_answers.get(str(i), [])
                if not isinstance(current_answers, list):
                    current_answers = [current_answers] if current_answers else []
                
                selected_options = []
                
                # Display checkboxes in columns for better layout
                cols = st.columns(min(3, len(display_options)))
                for idx, opt in enumerate(display_options):
                    col_idx = idx % len(cols)
                    with cols[col_idx]:
                        is_checked = st.checkbox(
                            opt,
                            value=opt in current_answers,
                            key=f"match_multi_q{current_index}_item{i}_{idx}"
                        )
                        if is_checked:
                            selected_options.append(opt)
                
                if set(selected_options) != set(current_answers):
                    user_answers[str(i)] = selected_options
                    answer_changed = True
                
                if selected_options:
                    st.success(f"✓ Selected: {', '.join(selected_options)}")
                
            else:
                # Single select dropdown
                current_answer = user_answers.get(str(i), "")
                
                selected_answer = st.selectbox(
                    f"Select match",
                    [""] + display_options,
                    index=0 if not current_answer else ([""] + display_options).index(current_answer) if current_answer in display_options else 0,
                    key=f"match_q{current_index}_item{i}",
                    label_visibility="collapsed"
                )
                
                if selected_answer != current_answer:
                    user_answers[str(i)] = selected_answer
                    answer_changed = True
    
    if answer_changed:
        st.session_state.user_answers[current_index] = user_answers.copy()
        st.rerun()
    
    # Progress indicator
    total_items = len(matching_items)
    if is_multi_select:
        answered_items = sum(1 for i in range(total_items) if user_answers.get(str(i)))
    else:
        answered_items = sum(1 for i in range(total_items) if user_answers.get(str(i)))
    
    if answered_items == total_items:
        st.success(f"✅ All {total_items} items answered!")
    else:
        st.warning(f"⏳ {answered_items}/{total_items} items answered")
    
    render_question_navigation()

def display_firewall_pbq(question):
    """Display firewall rules PBQ"""
    pbq_data = question.get('pbq_data', {})
    current_index = st.session_state.current_question_index
    
    # Display scenario image if available
    image_filename = question.get('scenario_image_filename')
    if image_filename:
        try:
            image_path = os.path.join('data/images', image_filename)
            if os.path.exists(image_path):
                st.image(image_path, caption="Network Diagram", use_container_width=600)
        except Exception:
            pass
    
    with st.container():
        st.info(f"📋 {pbq_data.get('instructions', 'Configure the firewall rules')}")
    
    # Initialize user answers
    if current_index not in st.session_state.user_answers:
        st.session_state.user_answers[current_index] = {}
    
    user_answers = st.session_state.user_answers[current_index]
    firewall_rules = pbq_data.get('firewall_rules', [])
    
    # Shuffle options if enabled
    shuffled_rules = []
    for rule_idx, rule in enumerate(firewall_rules):
        shuffled_rule = rule.copy()
        
        if st.session_state.shuffle_options:
            for field in ['rule_options', 'source_ip_options', 'dest_ip_options', 'protocol_options', 'port_options', 'action_options']:
                shuffle_key = f"shuffled_{current_index}_{rule_idx}_{field}"
                if shuffle_key not in st.session_state:
                    st.session_state[shuffle_key] = random.sample(rule[field], len(rule[field]))
                shuffled_rule[field] = st.session_state[shuffle_key]
        
        shuffled_rules.append(shuffled_rule)
    
    answer_changed = False
    
    st.markdown("### Firewall Rules Configuration")
    
    for i, rule in enumerate(shuffled_rules):
        with st.container():
            st.markdown(f"**Rule {i+1}**")
            
            cols = st.columns(6)
            
            # Rule Number
            with cols[0]:
                current_val = user_answers.get(f"{i}_rule", "")
                options = [""] + rule['rule_options']
                idx = options.index(current_val) if current_val in options else 0
                
                rule_num = st.selectbox(
                    "Rule #",
                    options,
                    index=idx,
                    key=f"fw_q{current_index}_r{i}_rule"
                )
            
            # Source IP
            with cols[1]:
                current_val = user_answers.get(f"{i}_source_ip", "")
                options = [""] + rule['source_ip_options']
                idx = options.index(current_val) if current_val in options else 0
                
                source_ip = st.selectbox(
                    "Source IP",
                    options,
                    index=idx,
                    key=f"fw_q{current_index}_r{i}_src"
                )
            
            # Destination IP
            with cols[2]:
                current_val = user_answers.get(f"{i}_dest_ip", "")
                options = [""] + rule['dest_ip_options']
                idx = options.index(current_val) if current_val in options else 0
                
                dest_ip = st.selectbox(
                    "Dest IP",
                    options,
                    index=idx,
                    key=f"fw_q{current_index}_r{i}_dst"
                )
            
            # Protocol
            with cols[3]:
                current_val = user_answers.get(f"{i}_protocol", "")
                options = [""] + rule['protocol_options']
                idx = options.index(current_val) if current_val in options else 0
                
                protocol = st.selectbox(
                    "Protocol",
                    options,
                    index=idx,
                    key=f"fw_q{current_index}_r{i}_proto"
                )
            
            # Port
            with cols[4]:
                current_val = user_answers.get(f"{i}_port", "")
                options = [""] + rule['port_options']
                idx = options.index(current_val) if current_val in options else 0
                
                port = st.selectbox(
                    "Port",
                    options,
                    index=idx,
                    key=f"fw_q{current_index}_r{i}_port"
                )
            
            # Action
            with cols[5]:
                current_val = user_answers.get(f"{i}_action", "")
                options = [""] + rule['action_options']
                idx = options.index(current_val) if current_val in options else 0
                
                action = st.selectbox(
                    "Action",
                    options,
                    index=idx,
                    key=f"fw_q{current_index}_r{i}_action"
                )
            
            # Check for changes
            new_answers = {
                f"{i}_rule": rule_num,
                f"{i}_source_ip": source_ip,
                f"{i}_dest_ip": dest_ip,
                f"{i}_protocol": protocol,
                f"{i}_port": port,
                f"{i}_action": action
            }
            
            for key, value in new_answers.items():
                if user_answers.get(key) != value:
                    user_answers[key] = value
                    answer_changed = True
    
    if answer_changed:
        st.session_state.user_answers[current_index] = user_answers.copy()
        st.rerun()
    
    # Progress indicator
    total_rules = len(firewall_rules)
    completed_rules = sum(1 for i in range(total_rules) if all(
        user_answers.get(f"{i}_{field}") for field in ['rule', 'source_ip', 'dest_ip', 'protocol', 'port', 'action']
    ))
    
    if completed_rules == total_rules:
        st.success(f"✅ All {total_rules} rules configured!")
    else:
        st.warning(f"⏳ {completed_rules}/{total_rules} rules configured")
    
    render_question_navigation()

def render_question_navigation():
    """Render question navigation buttons with validation"""
    current_index = st.session_state.current_question_index
    question = st.session_state.selected_questions[current_index]
    user_answer = st.session_state.user_answers.get(current_index, {})
    
    # Check if all fields are answered
    all_answered = False
    if question.get('is_pbq'):
        pbq_type = question.get('type', '').replace('PBQ - ', '')
        
        if pbq_type == "Classification/Matching":
            matching_items = question.get('pbq_data', {}).get('matching_items', [])
            is_multi_select = question.get('pbq_data', {}).get('is_multi_select', False)
            
            if is_multi_select:
                # For multi-select, check if each item has at least one answer
                all_answered = all(
                    user_answer.get(str(i)) and len(user_answer.get(str(i), [])) > 0 
                    for i in range(len(matching_items))
                )
            else:
                # For single select, check if all items have an answer
                all_answered = all(user_answer.get(str(i)) for i in range(len(matching_items)))
        
        elif pbq_type == "Firewall Rules":
            firewall_rules = question.get('pbq_data', {}).get('firewall_rules', [])
            fields = ['rule', 'source_ip', 'dest_ip', 'protocol', 'port', 'action']
            all_answered = all(
                user_answer.get(f"{i}_{field}") 
                for i in range(len(firewall_rules)) 
                for field in fields
            )
    else:
        all_answered = user_answer is not None and user_answer != ""
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_index > 0:
            if st.button("← Previous", key="prev_btn", use_container_width=True):
                st.session_state.current_question_index -= 1
                st.rerun()
    
    with col2:
        if not all_answered:
            st.warning("⚠️ Please answer all fields before proceeding")
    
    with col3:
        if current_index < len(st.session_state.selected_questions) - 1:
            if st.button("Next →", key="next_btn", use_container_width=True, disabled=not all_answered):
                if all_answered:
                    st.session_state.current_question_index += 1
                    st.rerun()
        else:
            if st.button("✅ Submit", type="primary", key="submit_btn", use_container_width=True, disabled=not all_answered):
                if all_answered:
                    end_practice_session()

def display_session_summary():
    """Display detailed session summary with item-by-item breakdown"""
    st.subheader("📊 Session Complete - Detailed Results")
    
    score = st.session_state.real_time_score
    total_questions = len(st.session_state.selected_questions)
    
    # Overall summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Questions", total_questions)
    with col2:
        st.metric("Correct", score['correct'], delta=f"{score['accuracy']:.0f}%")
    with col3:
        st.metric("Incorrect", score['incorrect'])
    with col4:
        st.metric("Accuracy", f"{score['accuracy']:.0f}%")
    
    # Performance feedback with 80% passing threshold
    if score['accuracy'] == 100:
        st.success("🏆 Perfect Score! Excellent Performance!")
    elif score['accuracy'] >= 80:
        st.success("✅ Pass! Great Job!")
    else:
        st.error("📉 Below 80% - Needs Improvement")
    
    st.markdown("---")
    
    # Detailed breakdown
    st.subheader("📋 Detailed Question Breakdown")
    
    for result in st.session_state.detailed_results:
        q_num = result['question_num']
        q_type = result['question_type']
        score_val = result.get('score', 0)
        total_val = result.get('total', 0)
        
        with st.expander(f"**PBQ{q_num} - {q_type}**: {result.get('instructions', '')} | Score: {score_val}/{total_val}", expanded=True):
            
            if q_type == "Classification/Matching":
                # Display classification results
                for item in result['items']:
                    is_multi = item.get('is_multi_select', False)
                    
                    # Format answers for display
                    if is_multi:
                        user_ans_display = ', '.join(item['user_answer']) if isinstance(item['user_answer'], list) else item['user_answer']
                        correct_ans_display = ', '.join(item['correct_answer']) if isinstance(item['correct_answer'], list) else item['correct_answer']
                    else:
                        user_ans_display = item['user_answer']
                        correct_ans_display = item['correct_answer']
                    
                    # Create compact container with icon
                    with st.container():
                        if item['is_correct']:
                            st.markdown(f"""
                            <div style="background-color: #1e4d2b; padding: 8px 12px; border-radius: 4px; margin: 4px 0; max-width: 800px;">
                                <strong>✓ {item['number']}. Correct:</strong> {user_ans_display}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background-color: #4d1e1e; padding: 8px 12px; border-radius: 4px; margin: 4px 0; max-width: 800px;">
                                <strong>✗ {item['number']}. Wrong:</strong> {user_ans_display}<br>
                                <strong>Correct Answer:</strong> {correct_ans_display}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.caption(f"*{item['description']}*")
            
            elif q_type == "Firewall Rules":
                # Display firewall results
                st.info(f"**Overall Score:** {score_val}/{total_val} fields correct | **Rows:** {result.get('rows_correct', 0)}/{result.get('rows_total', 0)} completely correct")
                
                for row in result['items']:
                    row_num = row['rule_number']
                    row_score = row['row_score']
                    row_total = row['row_total']
                    
                    # Compact header with icon
                    if row_score == row_total:
                        st.markdown(f"""
                        <div style="background-color: #1e4d2b; padding: 8px 12px; border-radius: 4px; margin: 8px 0; max-width: 900px;">
                            <strong>✓ Rule {row_num}:</strong> {row_score}/{row_total} correct - Perfect!
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color: #4d1e1e; padding: 8px 12px; border-radius: 4px; margin: 8px 0; max-width: 900px;">
                            <strong>✗ Rule {row_num}:</strong> {row_score}/{row_total} correct
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # User answer table - compact
                    st.markdown("**Your Answer:**")
                    cols = st.columns(6)
                    headers = ["Rule #", "Source IP", "Dest IP", "Protocol", "Port", "Action"]
                    
                    for idx, (col, header) in enumerate(zip(cols, headers)):
                        field_name = ['rule', 'source_ip', 'dest_ip', 'protocol', 'port', 'action'][idx]
                        value = row['user_row'].get(field_name, "")
                        is_correct = row['fields'][idx]['is_correct']
                        
                        with col:
                            st.markdown(f"<small><strong>{header}</strong></small>", unsafe_allow_html=True)
                            if is_correct:
                                st.markdown(f"""
                                <div style="background-color: #1e4d2b; padding: 4px 8px; border-radius: 3px; text-align: center;">
                                    ✓ {value}
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style="background-color: #4d1e1e; padding: 4px 8px; border-radius: 3px; text-align: center;">
                                    ✗ {value}
                                </div>
                                """, unsafe_allow_html=True)
                    
                    # Correct answer table - compact
                    st.markdown("**Correct Answer:**")
                    cols = st.columns(6)
                    
                    for idx, (col, header) in enumerate(zip(cols, headers)):
                        field_name = ['rule', 'source_ip', 'dest_ip', 'protocol', 'port', 'action'][idx]
                        value = row['correct_row'].get(field_name, "")
                        
                        with col:
                            st.markdown(f"<small><strong>{header}</strong></small>", unsafe_allow_html=True)
                            st.markdown(f"""
                            <div style="background-color: #1e3a4d; padding: 4px 8px; border-radius: 3px; text-align: center;">
                                {value}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("<div style='margin: 12px 0; border-top: 1px solid #444;'></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🔄 Start New Practice", type="primary", key="new_practice_session", use_container_width=True):
        st.session_state.practice_started = False
        st.session_state.show_answers = False
        st.session_state.user_answers = {}
        st.session_state.current_question_index = 0
        st.session_state.detailed_results = []
        st.rerun()("Needs Improvement")
    

# ============================================================================
# PBQ BUILDER UI
# ============================================================================

def render_pbq_builder():
    """Render the PBQ builder interface"""
    st.header("🛠️ PBQ Builder")
    st.info("Create exam-style performance-based questions")
    
    template = st.selectbox(
        "Choose PBQ Template:",
        ["Classification/Matching (Attack Types)", "Firewall Rules"],
        key="pbq_template_select"
    )
    
    st.markdown("---")
    
    if template == "Classification/Matching (Attack Types)":
        render_matching_builder()
    elif template == "Firewall Rules":
        render_firewall_builder()

def render_matching_builder():
    """Render matching PBQ builder"""
    st.subheader("📋 Classification/Matching Template")
    
    instructions = st.text_area(
        "Instructions",
        "Match the description with the most accurate attack type. Not all attack types will be used.",
        height=60,
        key="matching_instructions"
    )
    
    st.markdown("---")
    
    # Image upload
    scenario_image = st.file_uploader(
        "🖼️ Scenario Image (Optional)",
        type=['png', 'jpg', 'jpeg'],
        key="matching_image"
    )
    
    # NEW: Answer type selection
    st.markdown("### Answer Type")
    answer_type = st.radio(
        "Select answer format:",
        ["Single Select (One answer per item)", "Multi-Select (Multiple answers per item)"],
        help="Single Select: Each item has ONE correct answer | Multi-Select: Each item can have MULTIPLE correct answers",
        key="answer_type_radio"
    )
    is_multi_select = "Multi-Select" in answer_type
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Available Options")
        all_options = st.text_area(
            "All Available Options (one per line)",
            "On-path\nKeylogger\nRootkit\nInjection\nRFID cloning\nVishing\nDDoS\nSupply chain",
            height=200,
            key="matching_options"
        )
    
    with col2:
        st.markdown("### Items to Match")
        matching_items = st.text_area(
            "Descriptions to Match (one per line)",
            "Attacker obtains bank account number by calling victim\nAttacker accesses database from web browser\nAttacker intercepts client-server communication\nMultiple attackers overwhelm web server\nAttacker obtains login credentials",
            height=200,
            key="matching_items"
        )
    
    st.markdown("---")
    st.markdown("### Set Correct Answers")
    
    items_list = [item.strip() for item in matching_items.split('\n') if item.strip()]
    options_list = [opt.strip() for opt in all_options.split('\n') if opt.strip()]
    
    correct_answers = {}
    
    for i, item in enumerate(items_list):
        st.markdown(f"**{i+1}.** {item}")
        
        if is_multi_select:
            # Multi-select with checkboxes
            st.write("Select all that apply:")
            selected_options = []
            
            cols = st.columns(min(3, len(options_list)))
            for idx, opt in enumerate(options_list):
                col_idx = idx % len(cols)
                with cols[col_idx]:
                    if st.checkbox(opt, key=f"matching_multi_correct_{i}_{idx}"):
                        selected_options.append(opt)
            
            correct_answers[str(i)] = selected_options
            
            if selected_options:
                st.info(f"✓ Selected: {', '.join(selected_options)}")
            else:
                st.warning("⚠️ No answers selected")
        else:
            # Single select dropdown
            correct_answer = st.selectbox(
                f"Correct match",
                [""] + options_list,
                key=f"matching_correct_{i}",
                label_visibility="collapsed"
            )
            correct_answers[str(i)] = correct_answer
    
    st.markdown("---")
    
    if st.button("💾 Save PBQ", type="primary", key="save_matching", use_container_width=True):
        # Validation
        if is_multi_select:
            missing = [i+1 for i, item in enumerate(items_list) if not correct_answers.get(str(i))]
        else:
            missing = [i+1 for i, item in enumerate(items_list) if not correct_answers.get(str(i))]
        
        if missing:
            st.error(f"❌ Please set correct answers for items: {missing}")
            return
        
        pbq_data = {
            "instructions": instructions,
            "scenario_image": scenario_image.read() if scenario_image else None,
            "scenario_image_type": scenario_image.type if scenario_image else None,
            "matching_items": items_list,
            "all_options": options_list,
            "correct_answers": correct_answers,
            "is_multi_select": is_multi_select
        }
        
        save_pbq_question(pbq_data, "Classification/Matching")

def render_firewall_builder():
    """Render firewall rules PBQ builder"""
    st.subheader("🔥 Firewall Rules Template")
    
    instructions = st.text_area(
        "Instructions",
        "Configure the firewall rules according to the network diagram. Select the appropriate values for each rule.",
        height=60,
        key="firewall_instructions"
    )
    
    st.markdown("---")
    
    # Image upload
    scenario_image = st.file_uploader(
        "🖼️ Network Diagram (Recommended)",
        type=['png', 'jpg', 'jpeg'],
        key="firewall_image"
    )
    
    st.markdown("---")
    st.markdown("### Firewall Rules Configuration")
    
    num_rules = st.number_input("Number of Rules", min_value=1, max_value=10, value=3, key="num_rules")
    
    firewall_rules = []
    
    for i in range(num_rules):
        with st.expander(f"Rule {i+1} Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Available Options:**")
                rule_options = st.text_input(
                    "Rule Numbers (comma-separated)",
                    "1, 2, 3",
                    key=f"fw_rule_opts_{i}"
                )
                
                source_ips = st.text_input(
                    "Source IPs (comma-separated)",
                    "10.1.1.2, 10.2.1.33, 10.2.1.47",
                    key=f"fw_src_opts_{i}"
                )
                
                dest_ips = st.text_input(
                    "Destination IPs (comma-separated)",
                    "10.1.1.3, 10.1.1.7, 10.2.1.20",
                    key=f"fw_dst_opts_{i}"
                )
                
                protocols = st.text_input(
                    "Protocols (comma-separated)",
                    "TCP, UDP",
                    key=f"fw_proto_opts_{i}"
                )
                
                ports = st.text_input(
                    "Ports (comma-separated)",
                    "22, 80, 443",
                    key=f"fw_port_opts_{i}"
                )
                
                actions = st.text_input(
                    "Actions (comma-separated)",
                    "Allow, Block",
                    key=f"fw_action_opts_{i}"
                )
            
            with col2:
                st.markdown("**Correct Answers:**")
                correct_rule = st.selectbox(
                    "Rule #",
                    [x.strip() for x in rule_options.split(',')],
                    key=f"fw_correct_rule_{i}"
                )
                
                correct_src = st.selectbox(
                    "Source IP",
                    [x.strip() for x in source_ips.split(',')],
                    key=f"fw_correct_src_{i}"
                )
                
                correct_dst = st.selectbox(
                    "Destination IP",
                    [x.strip() for x in dest_ips.split(',')],
                    key=f"fw_correct_dst_{i}"
                )
                
                correct_proto = st.selectbox(
                    "Protocol",
                    [x.strip() for x in protocols.split(',')],
                    key=f"fw_correct_proto_{i}"
                )
                
                correct_port = st.selectbox(
                    "Port",
                    [x.strip() for x in ports.split(',')],
                    key=f"fw_correct_port_{i}"
                )
                
                correct_action = st.selectbox(
                    "Action",
                    [x.strip() for x in actions.split(',')],
                    key=f"fw_correct_action_{i}"
                )
            
            rule_data = {
                'rule_options': [x.strip() for x in rule_options.split(',')],
                'source_ip_options': [x.strip() for x in source_ips.split(',')],
                'dest_ip_options': [x.strip() for x in dest_ips.split(',')],
                'protocol_options': [x.strip() for x in protocols.split(',')],
                'port_options': [x.strip() for x in ports.split(',')],
                'action_options': [x.strip() for x in actions.split(',')],
                'correct_rule': correct_rule,
                'correct_source_ip': correct_src,
                'correct_dest_ip': correct_dst,
                'correct_protocol': correct_proto,
                'correct_port': correct_port,
                'correct_action': correct_action
            }
            
            firewall_rules.append(rule_data)
    
    st.markdown("---")
    
    if st.button("💾 Save PBQ", type="primary", key="save_firewall", use_container_width=True):
        # Build correct answers dictionary
        correct_answers = {}
        for i, rule in enumerate(firewall_rules):
            correct_answers[f"{i}_rule"] = rule['correct_rule']
            correct_answers[f"{i}_source_ip"] = rule['correct_source_ip']
            correct_answers[f"{i}_dest_ip"] = rule['correct_dest_ip']
            correct_answers[f"{i}_protocol"] = rule['correct_protocol']
            correct_answers[f"{i}_port"] = rule['correct_port']
            correct_answers[f"{i}_action"] = rule['correct_action']
        
        pbq_data = {
            "instructions": instructions,
            "scenario_image": scenario_image.read() if scenario_image else None,
            "scenario_image_type": scenario_image.type if scenario_image else None,
            "firewall_rules": firewall_rules,
            "correct_answers": correct_answers
        }
        
        save_pbq_question(pbq_data, "Firewall Rules")

def save_pbq_question(pbq_data: dict, pbq_type: str):
    """Save PBQ question to question bank"""
    pbq_data_clean = pbq_data.copy()
    image_filename = None
    scenario_image = pbq_data.get('scenario_image')
    scenario_image_type = pbq_data.get('scenario_image_type')
    
    # Save image to file if it exists
    if scenario_image and scenario_image_type:
        os.makedirs('data/images', exist_ok=True)
        
        image_filename = f"pbq_image_{len(st.session_state.question_bank)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        extension_map = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg'
        }
        extension = extension_map.get(scenario_image_type, '.png')
        image_filename += extension
        
        image_path = os.path.join('data/images', image_filename)
        with open(image_path, 'wb') as f:
            f.write(scenario_image)
    
    # Remove image bytes from JSON data
    if 'scenario_image' in pbq_data_clean:
        del pbq_data_clean['scenario_image']
    
    # IMPORTANT: Keep is_multi_select flag
    is_multi_select = pbq_data.get('is_multi_select', False)
    
    # Create question format
    standard_question = {
        "type": f"PBQ - {pbq_type}",
        "scenario": f"PBQ Instructions: {pbq_data.get('instructions', 'Complete the exercise below')}",
        "question": f"PBQ: {pbq_type}",
        "options": ["Start PBQ Exercise"],
        "correct_answer": json.dumps(pbq_data.get("correct_answers", {})),
        "explanation": "Performance-based question exercise",
        "is_pbq": True,
        "pbq_data": pbq_data_clean,
        "scenario_image_filename": image_filename,
        "scenario_image_type": scenario_image_type,
        "has_scenario_image": scenario_image is not None
    }
    
    st.session_state.question_bank.append(standard_question)
    
    if save_question_bank():
        st.success(f"✅ PBQ saved! Question bank now has {len(st.session_state.question_bank)} questions.")
        st.balloons()
    else:
        st.error("❌ Failed to save PBQ to file!")

# ============================================================================
# QUESTION BANK UI
# ============================================================================

def render_question_bank():
    """Render the question bank management interface"""
    st.header("📚 Question Bank")
    
    # Save status
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if os.path.exists('data/question_bank.json'):
            file_size = os.path.getsize('data/question_bank.json')
            st.success(f"✅ Questions saved to file ({file_size} bytes)")
        else:
            st.warning("⚠️ No saved questions file")
    
    with col2:
        if st.button("💾 Save Now", key="force_save_btn", use_container_width=True):
            if save_question_bank():
                st.success("Saved!")
                st.rerun()
    
    st.markdown("---")
    
    if not st.session_state.question_bank:
        st.info("📝 No questions in the bank yet. Use the PBQ Builder to create questions.")
        return
    
    # Statistics
    total_questions = len(st.session_state.question_bank)
    pbq_count = sum(1 for q in st.session_state.question_bank if q.get('is_pbq'))
    regular_count = total_questions - pbq_count
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Questions", total_questions)
    with col2:
        st.metric("PBQ Questions", pbq_count)
    with col3:
        st.metric("Regular Questions", regular_count)
    
    st.markdown("---")
    
    # Question list
    st.subheader("Question List")
    
    for i, question in enumerate(st.session_state.question_bank):
        question_type = question.get('type', 'Unknown')
        is_pbq = question.get('is_pbq', False)
        
        with st.expander(f"{'🎯' if is_pbq else '📝'} Q{i+1}: {question_type}", expanded=False):
            st.markdown(f"**Type:** {question_type}")
            
            if is_pbq:
                pbq_data = question.get('pbq_data', {})
                st.markdown(f"**Instructions:** {pbq_data.get('instructions', 'N/A')[:100]}...")
                
                if question.get('has_scenario_image'):
                    st.caption("🖼️ Has scenario image")
            else:
                st.markdown(f"**Question:** {question.get('question', 'N/A')[:100]}...")
                st.markdown(f"**Options:** {len(question.get('options', []))} choices")
            
            if st.button(f"🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                remove_question(i)
                st.rerun()
    
    st.markdown("---")
    
    # Clear all
    if total_questions > 0:
        st.subheader("⚠️ Danger Zone")
        if st.button("🧹 Clear All Questions", type="secondary", key="clear_all_btn"):
            st.session_state.clear_confirm = True
        
        if st.session_state.get('clear_confirm'):
            st.error("🚨 This will delete ALL questions permanently!")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Delete All", type="primary", key="confirm_clear"):
                    clear_all_questions()
                    st.session_state.clear_confirm = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", key="cancel_clear"):
                    st.session_state.clear_confirm = False
                    st.rerun()

def remove_question(index):
    """Remove a specific question"""
    try:
        if 0 <= index < len(st.session_state.question_bank):
            st.session_state.question_bank.pop(index)
            
            if save_question_bank():
                st.success("Question removed!")
            else:
                st.error("Failed to save after removal!")
    except Exception as e:
        st.error(f"Error removing question: {e}")

def clear_all_questions():
    """Clear all questions from the bank"""
    try:
        st.session_state.question_bank = []
        
        if save_question_bank():
            st.success("All questions cleared!")
        else:
            st.error("Failed to save after clearing!")
    except Exception as e:
        st.error(f"Error clearing questions: {e}")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    initialize_session_state()
    
    # Sidebar navigation
    st.sidebar.title("🛸 Yoshi, ikou!")
    st.sidebar.markdown("---")
    
    # Page selection based on SHOW_BUILDER flag
    if SHOW_BUILDER:
        page_options = ["Practice Mode", "PBQ Builder", "Question Bank"]
    else:
        page_options = ["Practice Mode"]
    
    page = st.sidebar.radio(
        "Navigation",
        page_options,
        index=0
    )
    
    st.session_state.current_page = page
    
    # Main content area
    st.markdown("---")
    
    # Page routing
    if page == "Practice Mode":
        render_practice_mode()
    elif page == "PBQ Builder" and SHOW_BUILDER:
        render_pbq_builder()
    elif page == "Question Bank" and SHOW_BUILDER:
        render_question_bank()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("💡 Gambare! v2.0")
    if SHOW_BUILDER:
        st.sidebar.caption("🛠️ Builder Mode: Active")
    else:
        st.sidebar.caption("👥 Public Mode: Practice Only")

if __name__ == "__main__":
    main()