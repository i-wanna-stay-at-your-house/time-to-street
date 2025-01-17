import streamlit as st
import openai
import os
import pandas as pd
import datetime


st.title('TIME TO STREET')

num_participants = st.sidebar.number_input('참여자 수', min_value=1, max_value=10, value=3)

# 요일 목록
days_of_week = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']

# 호스트가 제외하고 싶은 시간대를 설정
st.sidebar.subheader("호스트 제외 시간대 설정")
exclude_time_checkbox = st.sidebar.checkbox('새벽 시간을 제외할 것인가요?')

if exclude_time_checkbox:
    time_options = [f'{hour:02d}:{minute:02d}' for hour in range(23, 24) for minute in range(0, 60, 5)] + \
                   [f'{hour:02d}:{minute:02d}' for hour in range(0, 8) for minute in range(0, 60, 5)]
    
    exclude_start_time_str = st.sidebar.selectbox('새벽 시간 시작', options=time_options, index=0)
    exclude_end_time_str = st.sidebar.selectbox('새벽 시간 끝', options=time_options, index=len(time_options) - 1)
    
    exclude_start_time = datetime.datetime.strptime(exclude_start_time_str, "%H:%M").time()
    exclude_end_time = datetime.datetime.strptime(exclude_end_time_str, "%H:%M").time()
else:
    exclude_start_time = None
    exclude_end_time = None
    
    
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
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.sidebar.write(f"{name}의 {day} 불가능 시간 (예: 12:00-15:00, 17:00-21:00)")
        with col2:
            all_day_unavailable = st.sidebar.checkbox('모든 시간 불가능', key=f'all_day_{i}_{j}')
        
        if all_day_unavailable:
            unavailability[day] = "00:00-24:00"
            st.sidebar.write(f"{day} 모든 시간 불가능")
        else:
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

def find_optimal_schedule(participants, required_participants, excluded_participants, exclude_start_time, exclude_end_time):
    prompt = "다음 데이터는 모임에 참여하는 참여자의 이름과 해당 참여자가 특정 요일에 참여가 불가능한 시간들을 나타냅니다. 참여자들의 모든 불가능한 시간들의 합집합을 제외한 '모든' 시간을 제시해주면 됩니다. 예를 들어 월요일에 첫번째 참가자는 12:00-14:00, 16:00-18:00 해당 시간이 불가능 시간이고, 두번째 참가자는 15:00-17:00, 19:00-21:00라면 12:00-14:00, 15:00-18:00, 19:00-21:00을 제외한 모든 시간을 나타내주면 됩니다. 만약 00:00-24:00가 모두 안 된다면 '참여자들의 시간을 모두 고려하였을 때 해당 요일은 약속을 잡기 어려운 날로 인식됩니다.'로 나타내주면 됩니다. 그리고 각 참가자를 제외하였을 때 가능한 시간도 나타내주면 될 것 같습니다. \n"
    
    # 호스트가 제외하고 싶은 시간대를 추가
    if exclude_start_time and exclude_end_time:
        prompt += f"모든 요일의 제외 시간대: {exclude_start_time.strftime('%H:%M')} - {exclude_end_time.strftime('%H:%M')}\n"

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
    best_times = find_optimal_schedule(participants, required_participants, excluded_participants, exclude_start_time, exclude_end_time)
    
    st.write('## 추천 시간대')
    for time in best_times:
        st.write(time)
