import streamlit as st
import openai
import os

st.title('TIME TO STREET')

num_participants = st.sidebar.number_input('참여자 수', min_value=1, max_value=10, value=3)

# 요일 목록
days_of_week = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']

# 참가자의 이름과 안 되는 요일, 시간을 이중 dict 형태로 저장
participants = {}
participant_names = []
for i in range(num_participants):
    name = st.sidebar.text_input(f'참여자 {i+1} 이름', value=f'참여자 {i+1}', key=f'name_{i}')
    participant_names.append(name)
    unavailability = {}
    unavailable_days = st.sidebar.multiselect(f'{name}의 참여 불가능 요일 선택', days_of_week, key=f'days_{i}')
    
    # 선택된 요일을 days_of_week의 순서대로 정렬
    unavailable_days = sorted(unavailable_days, key=lambda day: days_of_week.index(day))

    for j, day in enumerate(unavailable_days):
        st.sidebar.write(f"{name}의 {day} 불가능 시간 (예: 12:00-15:00, 17:00-21:00)")
        times = st.sidebar.text_area(f'{day} 불가능 시간 입력', placeholder="12:00-15:00, 17:00-21:00", key=f'times_{i}_{j}')
        unavailability[day] = times    
        
    participants[name] = unavailability


# 참가자 이름을 알파벳 순으로 정렬
participant_names.sort()

st.write('## 참여자 목록 및 참여 불가능 시간')
for name, schedule in participants.items():
    st.write(f'**{name}**:')
    for day, times in schedule.items():
        st.write(f'  - {day}: {times}')


# 필수 고려 대상 참가자 선택
required_participants = st.multiselect(
    '필수 고려 대상 참가자 선택',
    participant_names,
    key='required_participants'
)

# 제외할 참가자 선택
excluded_participants = st.multiselect(
    '제외할 참가자 선택',
    participant_names,
    key='excluded_participants'
)


# 필수 고려 대상 참가자와 제외할 참가자를 알파벳 순으로 정렬
required_participants = sorted(required_participants)
excluded_participants = sorted(excluded_participants)


# API KEY 설정
api_key = os.getenv('OPENAI_API_KEY')  # 환경 변수에서 API 키를 가져옵니다.
openai.api_key = api_key

if not api_key:
    raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

def find_optimal_schedule(participants, required_participants, excluded_participants):
    prompt = "다음 참여자들의 불가능 시간을 고려하여 최적의 회의 시간을 추천해 주세요. 최적의 요일과 시간을 3가지 정도로 추려서 알려주면 됩니다. 따로 요청사항이 없다면 2시간 단위로 시간을 나누면 됩니다.\n"
    
    # 필수 고려 대상 참가자의 정보를 추가
    if required_participants:
        prompt += "필수 고려 대상 참가자:\n"
        for name in required_participants:
            prompt += f"{name}:\n"
            for day, times in participants[name].items():
                prompt += f"  {day}: {times}\n"
    
    # 제외할 참가자를 제외한 나머지 참가자의 정보를 추가
    prompt += "불가능한 시간대를 고려하지 않아도 되는 참가자(최적의 시간대를 조율할 때, 후순위로 고려해도 되는 참가자):\n"
    for name, schedule in participants.items():
        if name not in excluded_participants:
            prompt += f"{name}:\n"
            for day, times in schedule.items():
                prompt += f"  {day}: {times}\n"

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip().split('\n')

if st.button('최적의 시간대 찾기'):
    st.write('최적의 시간대를 찾는 중입니다...')
    best_times = find_optimal_schedule(participants, required_participants, excluded_participants)
    
    st.write('## 추천 시간대')
    for time in best_times:
        st.write(time)
