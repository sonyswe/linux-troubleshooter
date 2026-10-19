
import streamlit as st

st.set_page_config(
    page_title="Linux Troubleshooting AI Assistant",
    page_icon="🐧",
    layout="wide"
)

st.title("🐧 Linux Troubleshooting AI Assistant")
st.write(
    "A beginner-friendly demo for troubleshooting Linux, "
    "services, networking, and DevOps problems."
)

st.info(
    "Demo mode: This version works offline and does not require "
    "Ollama or an external AI API."
)

KNOWLEDGE = {
    "nginx": {
        "title": "Nginx service is not running",
        "keywords": ["nginx", "web server", "website not working"],
        "cause": (
            "Nginx may be stopped, its configuration may be invalid, "
            "or another process may be using port 80 or 443."
        ),
        "commands": [
            "sudo systemctl status nginx",
            "sudo nginx -t",
            "sudo journalctl -u nginx -n 50 --no-pager",
            "sudo systemctl restart nginx",
        ],
        "explanation": (
            "Check the service status first. Validate the configuration "
            "before restarting the service. Review logs if it still fails."
        ),
    },
    "disk": {
        "title": "Linux disk space is full",
        "keywords": ["disk", "space", "full", "storage"],
        "cause": (
            "Large log files, backups, temporary files, or unused data "
            "may be consuming disk space."
        ),
        "commands": [
            "df -h",
            "sudo du -xhd1 /var 2>/dev/null | sort -hr",
            "sudo journalctl --disk-usage",
        ],
        "explanation": (
            "Use df -h to identify a full filesystem. Use du to find "
            "large directories. Inspect files before deleting anything."
        ),
    },
    "memory": {
        "title": "High memory usage",
        "keywords": ["memory", "ram", "oom", "out of memory"],
        "cause": (
            "A process may be consuming excessive RAM, or the system "
            "may have insufficient memory for its workload."
        ),
        "commands": [
            "free -h",
            "top",
            "ps aux --sort=-%mem | head",
            "journalctl -k -n 50 --no-pager",
        ],
        "explanation": (
            "Check available memory and identify processes using the "
            "most RAM. Review kernel logs for out-of-memory events."
        ),
    },
    "network": {
        "title": "Network connectivity problem",
        "keywords": ["network", "internet", "connectivity", "dns"],
        "cause": (
            "The issue may be related to the network interface, "
            "routing, DNS resolution, or a remote server."
        ),
        "commands": [
            "ip addr",
            "ip route",
            "ping -c 4 8.8.8.8",
            "getent hosts google.com",
        ],
        "explanation": (
            "Check the interface and routing table first. Test IP "
            "connectivity, then check whether DNS names resolve."
        ),
    },
    "process": {
        "title": "Linux process is consuming high CPU",
        "keywords": ["cpu", "process", "slow", "performance"],
        "cause": (
            "A process may be stuck in a loop, processing heavy work, "
            "or consuming more CPU than expected."
        ),
        "commands": [
            "top",
            "ps aux --sort=-%cpu | head",
            "pgrep -a PROCESS_NAME",
            "ps -p PID -o pid,ppid,stat,%cpu,%mem,cmd",
        ],
        "explanation": (
            "Identify the process using CPU. Replace PROCESS_NAME and "
            "PID with actual values. Investigate before stopping it."
        ),
    },
}


def troubleshoot(question):
    question = question.lower()

    for item in KNOWLEDGE.values():
        if any(keyword in question for keyword in item["keywords"]):
            return item

    return {
        "title": "General Linux troubleshooting",
        "keywords": [],
        "cause": (
            "The problem may involve services, permissions, "
            "configuration, resources, or connectivity."
        ),
        "commands": [
            "whoami",
            "uptime",
            "df -h",
            "free -h",
            "systemctl --failed",
        ],
        "explanation": (
            "Start by collecting system information. Check relevant "
            "service logs and configuration files before making changes."
        ),
    }


with st.sidebar:
    st.header("About this project")
    st.write("Linux troubleshooting knowledge demo")
    st.write("Technologies: Python and Streamlit")
    st.write("Mode: Offline, rule-based demonstration")

    st.subheader("Try an example")
    examples = [
        "Nginx service is not running",
        "My disk space is full",
        "How do I check high memory usage?",
        "I have a network connectivity problem",
        "A process is consuming high CPU",
    ]

    selected_example = st.selectbox(
        "Choose a Linux problem",
        ["Select an example"] + examples,
    )

st.subheader("Describe your Linux problem")

question = st.text_area(
    "What issue are you facing?",
    placeholder=(
        "Example: Nginx is not running. "
        "How can I troubleshoot it?"
    ),
    height=120,
)

if st.button("Troubleshoot", type="primary"):
    if question.strip():
        result = troubleshoot(question)

        st.subheader(result["title"])

        st.markdown("**Possible cause**")
        st.write(result["cause"])

        st.markdown("**Recommended commands**")
        for command in result["commands"]:
            st.code(command, language="bash")

        st.markdown("**Troubleshooting guidance**")
        st.write(result["explanation"])

        st.warning(
            "Review commands before running them. This demo does not "
            "execute commands on your computer or inspect a live server."
        )
    else:
        st.warning("Please describe your Linux problem first.")

if selected_example != "Select an example":
    st.caption("Selected example: " + selected_example)
    if st.button("Use selected example"):
        st.session_state["example_question"] = selected_example
        st.rerun()

if "example_question" in st.session_state:
    st.write("Example problem: " + st.session_state["example_question"])
    st.caption(
        "Copy this example into the problem box above and click "
        "Troubleshoot."
    )

st.divider()
st.caption(
    "Linux Troubleshooting AI Assistant | Portfolio Demo"
)
