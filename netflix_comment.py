from datetime import datetime
import jieba
from wordcloud import WordCloud
import streamlit as st
import pandas as pd
from google.cloud import firestore
import matplotlib.pyplot as plt

# st.markdown(
#     f"""
#     <style>
#     .reportview-container {{
#         background-color: black
#     }}
#     </style>
#     """,
#     unsafe_allow_html=True
# )
st.set_option('deprecation.showPyplotGlobalUse', False)
df = firestore.Client.from_service_account_json(
    './netflix-comment-system-firebase-adminsdk-hq5cn-9c691199bd.json')

st.sidebar.title('Netflixm原創影劇評論檢索系統')
drama_list = [d.id for d in df.collection('Comments').get()]
selection = st.sidebar.selectbox(
    '展開列表選擇或直接搜尋', drama_list, drama_list.index('魷魚遊戲'))
st.title(selection)
query = selection

if query not in drama_list:
    st.write('Not found')
else:
    # Data Preparation

    # try:
    #     drama_df = pd.read_csv('./drama_complete_df.csv', index_col='name')
    #     drama_df['related_fb_post'] = drama_df['related_fb_post'].apply(
    #         lambda x: str(x)[1:-1].split(', ') if x != '[]' else [])
    #     comments_df = pd.read_csv(
    #         './Comments_from_fb.csv', index_col='comment_id')
    #     img_url = drama_df.loc[query]['img']
    #     introduction = drama_df.loc[query]['info']
    #     scores = {'豆瓣': drama_df.loc[query]['douban'], 'IMDb': drama_df.loc[query]['imdb'], '爛番茄': (
    #         drama_df.loc[query]['rt_tm'], drama_df.loc[query]['rt_ad'])}
    #     all_comment = []
    #     for c_id in drama_df.loc[query]['related_fb_post']:
    #         comment = comments_df.loc[int(c_id)]
    #         cm_dt = dict()
    #         try:
    #             cm_dt['time'] = comment['comment_time']
    #             cm_dt['text'] = comment['comment_text']
    #             cm_dt['sentiment'] = round(comment['sentiment']*10, 2)
    #             all_comment.append(cm_dt)
    #         except Exception as err:
    #             print(err)
    # except Exception as e:
    #     print(e)
    doc_ref = df.collection('Comments').document(query)
    doc_dt = doc_ref.get().to_dict()
    img_url = doc_ref.get().get('img')
    introduction = doc_ref.get().get('info')
    scores = {'豆瓣': doc_dt['豆瓣'], 'IMDb': doc_ref.get().get(
        'imdb'), '爛番茄': (doc_ref.get().get('rt_tm'), doc_ref.get().get('rt_aad'))}
    print('Scores loaded')
    data = []
    date = []
    all_comment = []
    for doc in doc_ref.collection('comments').stream():
        comment_id = doc.get('comment_id')
        if comment_id == "":
            continue
        cm_dt = dict()
        comment = df.collection('comments').document(
            str(comment_id)).get().to_dict()
        try:
            try:
                cm_dt['time'] = datetime.strptime(
                    str(comment['time']), '%Y-%m-%d %H:%M:%S')
            except:
                cm_dt['time'] = comment['time']
            cm_dt['text'] = comment['text']
            cm_dt['sentiment'] = round(comment['sentiment']*10, 2)
            all_comment.append(cm_dt)
            data.append(cm_dt['sentiment'])
            date.append(cm_dt['time'].strftime('%Y-%m-%d'))
        except Exception as err:
            print(err)
            continue
    print('fb comments loaded')

    dcard_comment = []
    for doc in doc_ref.collection('dcard_cms').stream():
        dt = doc.to_dict()
        c_dt = dict()
        c_dt['text'] = dt['text']
        c_dt['sentiment'] = round(dt['sentiment']*10, 2)
        dcard_comment.append(c_dt)
        data.append(c_dt['sentiment'])

    print('dcard comments loaded')

    jieba.dt.cache_file = 'jieba.cache.new'
    all_text = ""
    for cm in all_comment:
        all_text += cm['text']

    for cm in dcard_comment:
        all_text += cm['text']
    with open('./stopwords.txt') as fh:
        stopword = [d[:-1] for d in fh.readlines()]
    docs = ' '.join([w for w in jieba.cut(all_text)
                     if w not in stopword and len(w) > 3])
    try:
        wordcloud = WordCloud(
            margin=2, font_path='./setofont.ttf').generate(docs)
    except:
        pass
    # UI rendering
    if img_url != 'None':
        st.image(img_url, width=400)
    st.header('介紹')
    st.write(introduction)

    st.header('知名網站評分')
    ss = st.columns(3)
    source = ['豆瓣', 'IMDb', '爛番茄']
    for i in range(3):
        if i == 2:
            ss[i].subheader(source[i])
            ss[i].subheader('影評 - ' + str(scores[source[i]][0]))
            ss[i].subheader('觀眾 - ' + str(scores[source[i]][1]))
        else:
            ss[i].subheader(source[i])
            ss[i].subheader(str(scores[source[i]]) + '/10')

    pos_comment = [cm for cm in all_comment if 9 > cm['sentiment'] >= 5]
    neg_comment = [cm for cm in all_comment if 2 < cm['sentiment'] < 5]
    pos_comment.sort(key=lambda x: float(x['sentiment']), reverse=True)
    neg_comment.sort(key=lambda x: float(x['sentiment']))

    st.header('臉書網友這樣說')
    col1, col2 = st.columns(2)

    col1.subheader('喜歡的人認為')
    pc = pos_comment[:10] if len(pos_comment) > 10 else pos_comment
    for c in pc:
        sent = c['sentiment']
        col1.write('---')
        col1.write(c['text'])
        col1.markdown(
            f"<p style='text-align: right;'>情緒分數 {sent}/10</p>", unsafe_allow_html=True)
        # col1.write(f'給分 {sent}')
        col1.write(c['time'])

    col2.subheader('不喜歡的人認為')
    nc = neg_comment[:10] if len(neg_comment) > 10 else neg_comment
    for c in nc:
        sent = c['sentiment']
        col2.write('---')
        col2.write(c['text'])
        col2.markdown(
            f"<p style='text-align: right;'>情緒分數 {sent}/10</p>", unsafe_allow_html=True)
        # col2.write(f'給分 {sent}')
        col2.write(c['time'])

    if len(date) > 0:
        st.subheader('留言日期分佈')
        date = pd.DataFrame(date)
        try:
            date.value_counts(sort=False).plot(kind='bar')
            plt.tight_layout()
            plt.show()
            st.pyplot()
        except:
            pass

    pos_dc = [c for c in dcard_comment if 9.5 > c['sentiment'] > 5]
    neg_dc = [c for c in dcard_comment if 1.5 < c['sentiment'] < 5]
    pos_dc.sort(key=lambda x: float(x['sentiment']), reverse=True)
    neg_dc.sort(key=lambda x: float(x['sentiment']))
    st.header('迪卡網友這樣說')
    col1, col2 = st.columns(2)

    col1.subheader('喜歡的人認為')
    pc = pos_dc[:10] if len(pos_dc) > 10 else pos_dc
    for c in pc:
        sent = c['sentiment']
        col1.write('---')
        col1.write(c['text'])
        col1.markdown(
            f"<p style='text-align: right;'>情緒分數 {sent}/10</p>", unsafe_allow_html=True)

    col2.subheader('不喜歡的人認為')
    nc = neg_dc[:10] if len(neg_dc) > 10 else neg_dc
    for c in nc:
        sent = c['sentiment']
        col2.write('---')
        col2.write(c['text'])
        col2.markdown(
            f"<p style='text-align: right;'>情緒分數 {sent}/10</p>", unsafe_allow_html=True)

    if len(all_text) > 0:
        try:
            st.subheader('文字雲')
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis("off")
            plt.show()
            st.pyplot()
        except:
            pass

    if len(data) > 0:
        st.subheader('留言情緒分佈')
        n, bins, patches = plt.hist(data, bins=20)
        plt.xlabel("scores")
        plt.ylabel("frequency")
        plt.title("Sentiment Score Histogram Plot")
        plt.show()
        st.pyplot()
