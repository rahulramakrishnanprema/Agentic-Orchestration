from setuptools import setup, find_packages

setup(
    name="aristotle",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "langgraph>=0.0.15",
        "langchain-core>=0.1.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "pymongo>=4.6.0",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "pydantic>=2.5.0"
    ],
    author="Rahul",
    description="AI Development System with LangGraph Integration",
    python_requires=">=3.9",
)
