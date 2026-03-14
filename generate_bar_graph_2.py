import requests
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.patches import Patch

API_URL = "http://127.0.0.1:8000/reports/monthly-report/46/"

groups = {
    "Construction": [
        "Material Distributed Households",
        "Toilets Completed",
        "Toilets Under Construction"
    ],

    "Administration": [
        "Total Agreements",
        "Factsheets Assigned"
    ],

    "Mobilization Activities": [
        "Mobilization Activities Conducted OHOT",
        "Mobilization Activities Conducted MHM"
    ],

    "Mobilization Participation": [
        "Total Members Attended Mobilization OHOT",
        "Total Members Attended Mobilization MHM"
    ]
}

label_map = {
"Material Distributed Households": "Material\nDistributed",
"Toilets Completed": "Toilets\nCompleted",
"Toilets Under Construction": "Under\nConstruction",
"Total Agreements": "Agreements",
"Factsheets Assigned": "Factsheets",
"Mobilization Activities Conducted OHOT": "OHOT\nActivities",
"Mobilization Activities Conducted MHM": "MHM\nActivities",
"Total Members Attended Mobilization OHOT": "OHOT\nParticipants",
"Total Members Attended Mobilization MHM": "MHM\nParticipants"
}


def generate_chart():

    data = requests.get(API_URL).json()
    work_progress = data["work_progress"]

    locations = [loc["location"] for loc in work_progress]

    base_colors = [
        "#1F7A73","#F28E2B","#E15759","#EDC948","#4E79A7",
        "#76B7B2","#59A14F","#FF9DA7","#B07AA1","#9C755F"
    ]

    colors = base_colors[:len(locations)]

    fig, axes = plt.subplots(1,4, figsize=(7.3,3))

    for ax,(group_name,parameters) in zip(axes,groups.items()):

        values = []

        for loc in work_progress:
            param_dict = {p["parameter"]:p["value"] for p in loc["parameters"]}
            row = [param_dict.get(p,0) for p in parameters]
            values.append(row)

        values = np.array(values)

        x = np.arange(len(parameters))
        width = 0.8/len(locations)

        for i,loc in enumerate(locations):

            bars = ax.bar(
                x+i*width,
                values[i],
                width,
                color=colors[i]
            )

            for bar in bars:

                height = bar.get_height()

                if height > 0:
                    ax.text(
                        bar.get_x()+bar.get_width()/2,
                        height*0.5,
                        f"{int(height)}",
                        ha="center",
                        va="center",
                        fontsize=6,
                        fontweight="bold",
                        color="white"
                    )

        labels = [label_map[p] for p in parameters]

        ax.set_xticks(x + width*(len(locations)-1)/2)
        ax.set_xticklabels(labels, fontsize=6)

        ax.set_title(group_name, fontsize=7, fontweight="bold")

        ax.grid(axis="y", linestyle="--", alpha=0.3)


    legend_items = [
        Patch(facecolor=colors[i], label=locations[i])
        for i in range(len(locations))
    ]

    fig.legend(
        handles=legend_items,
        loc="upper center",
        bbox_to_anchor=(0.5,1.02),
        ncol=min(len(locations),2),
        fontsize=7,
        frameon=False
    )

    plt.subplots_adjust(top=0.75, wspace=0.4)

    home = os.path.expanduser("~")
    path = os.path.join(home,"donor_report_chart.png")

    plt.savefig(path, dpi=600, bbox_inches="tight")
    plt.close()

    print("Saved chart:",path)


generate_chart()
