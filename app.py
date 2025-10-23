import pandas as pd
from geopy.distance import geodesic
import streamlit as st
import folium
from streamlit_folium import st_folium

st.title("Northern Spain camping route optimizer")

# load data
campings = pd.read_csv("campings.csv")
campings["latitude"] = campings["latitude"].astype(str).str.replace(",", "").astype(float)
campings["longitude"] = campings["longitude"].astype(str).str.replace(",", "").astype(float)

# sidebar filters
st.sidebar.header("Filters")
start = st.sidebar.selectbox("Starting camping", campings["name"])
num_stops = st.sidebar.slider("Number of campings to visit", 2, len(campings), 4)
max_price = st.sidebar.slider("Max price per night (€)",int(campings["price per night"].min()),int(campings["price per night"].max()),50)
min_rating = st.sidebar.slider("Min rating", 0.0, 5.0, 2.0, 0.1)

# filter data
filtered = []
for i, row in campings.iterrows():
    if row["price per night"] <= max_price and row["rating"] >= min_rating:
        filtered.append(row)

filtered = pd.DataFrame(filtered)

# make sure the starting camping is included even if it doesn't meet the filters
if start not in filtered["name"].values:
    start_camping = campings[campings["name"] == start]
    filtered = pd.concat([start_camping, filtered]).reset_index(drop=True)

# n-n route
def get_route(data, start_name, n_stops):
    route = []
    current_idx = data[data["name"]==start_name].index[0]
    route.append(current_idx)

    while len(route) < n_stops:
        nearest = None
        nearest_dist = 999999
        for i in data.index:
            if i in route:
                continue
            dist = geodesic(
                (data.loc[current_idx, "latitude"], data.loc[current_idx, "longitude"]),
                (data.loc[i, "latitude"], data.loc[i, "longitude"])
            ).km
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = i
        route.append(nearest)
        current_idx = nearest
    return data.loc[route].reset_index(drop=True)

route_df = get_route(filtered, start, min(num_stops, len(filtered)))

# table
st.dataframe(route_df[["name", "type", "rating", "price per night"]])

# calculate summary
total_distance = 0
for i in range(1, len(route_df)):
    prev_lat = route_df.loc[i-1, "latitude"]
    prev_lon = route_df.loc[i-1, "longitude"]
    curr_lat = route_df.loc[i, "latitude"]
    curr_lon = route_df.loc[i, "longitude"]
    
    distance = geodesic((prev_lat, prev_lon), (curr_lat, curr_lon)).km
    total_distance += distance

total_cost = route_df["price per night"].sum()

# map
m = folium.Map(location=[route_df["latitude"].mean(), route_df["longitude"].mean()], zoom_start=7)

# markers
for idx, row in route_df.iterrows():
    if idx == 0:
        color = "green"
        label = "Start"
    elif idx == len(route_df)-1:
        color = "red"
        label = "End"
    else:
        color = "blue"
        label = ""

    if idx == 0:
        dist_text = "Start"
    else:
        prev_row = route_df.iloc[idx-1]
        dist_text = f"Distance from prev: {geodesic((prev_row['latitude'], prev_row['longitude']), (row['latitude'], row['longitude'])).km:.1f} km"

    folium.Marker(
        [row["latitude"], row["longitude"]],
        popup=f"{idx+1} - {row['name']}<br>{dist_text}<br>⭐ {row['rating']} | 💶 {row['price per night']}€",
        tooltip=f"{label} {row['name']}" if label else row['name'],
        icon=folium.DivIcon(html=f"""<div style="
            background:white; border:2px solid {color};
            border-radius:50%; width:28px; height:28px;
            text-align:center; line-height:28px;
            font-weight:bold; color:{color}">{idx+1}</div>""")
    ).add_to(m)

# route line
folium.PolyLine(route_df[["latitude","longitude"]].values.tolist(), color="blue", weight=3, opacity=0.7).add_to(m)

# legend top-right
legend_html = """
<div style="position: fixed; 
     top: 10px; right: 10px; width: 140px; height: 90px; 
     background-color:white; border:2px solid grey; z-index:9999; padding:10px;">
     <b>Legend</b><br>
     <span style="color:green">●</span> Start<br>
     <span style="color:red">●</span> End<br>
     <span style="color:blue">●</span> Intermediate
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

st.subheader("Route map")
st_folium(m, width=700, height=500)

# summary
st.subheader("Route summary")
st.markdown(f"- Total distance: **{total_distance:.1f} km**")
st.markdown(f"- Total cost: **€{total_cost}**")

# download route
st.subheader("Download route")
csv = route_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download route as CSV",
    data=csv,
    file_name='optimized_route.csv',
    mime='text/csv'
)