from akson import Agent, ChatAgent, SimpleAssistant

# {{{ input
company_name = """ACME Works, Inc."""

job_title = """Mid-Level Python Developer"""

job_description = """
    ## About the Role
    We're seeking a talented Mid-Level Python Developer who also has experience with React to join our growing engineering team. In this role, you'll work on both backend services and frontend applications, collaborating with cross-functional teams to deliver high-quality solutions.

    ## Key Responsibilities
    - Design and develop scalable Python applications and APIs using modern frameworks like Django or FastAPI
    - Build and maintain responsive frontend applications using React
    - Write clean, maintainable, and well-tested code
    - Participate in code reviews and contribute to technical discussions
    - Debug production issues and optimize application performance
    - Collaborate with product managers and designers to implement new features
    - Mentor junior developers and share knowledge with the team

    ## Required Qualifications
    - 3-5 years of professional software development experience
    - Strong proficiency in Python and its ecosystem
    - Experience with Python web frameworks (Django, Flask, or FastAPI)
    - Working knowledge of React and modern JavaScript
    - Solid understanding of RESTful APIs and microservices architecture
    - Proficient with Git version control
    - Experience with SQL databases and ORM frameworks
    - Strong problem-solving skills and attention to detail
    - Excellent written and verbal communication skills

    ## Nice to Have
    - Experience with TypeScript
    - Knowledge of Docker and containerization
    - Familiarity with AWS or other cloud platforms
    - Experience with CI/CD pipelines
    - Understanding of Agile development practices
    - Contributions to open-source projects

    ## Benefits
    - Competitive salary and equity package
    - Health, dental, and vision insurance
    - Flexible PTO policy
    - Remote work options
    - Professional development budget
    - 401(k) matching
    - Regular team events and activities

    ## Our Tech Stack
    - Backend: Python, Django/FastAPI, PostgreSQL
    - Frontend: React, TypeScript, Redux
    - Infrastructure: AWS, Docker, Kubernetes
    - Tools: Git, JIRA, CircleCI

    We're committed to building a diverse and inclusive workplace. We encourage applications from candidates of all backgrounds.
"""

# }}}


class InterviewPhase:
    def __init__(self, name, instructions, completion_criteria):
        self.name = name
        self.instructions = instructions
        self.completion_criteria = completion_criteria


# {{{ interview phases
introduction = InterviewPhase(
    name="Introduction",
    instructions="""
You are an AI interviewer for [Company Name]. Your role is to conduct a professional job interview for the [Job Title] position. Introduce yourself as an AI interviewer, explain that this is an automated interview process, and make the candidate comfortable. Your tone should be professional yet friendly.

Start with:
- A warm welcome
- Brief introduction of yourself as an AI interviewer
- Explanation of the interview process and expected duration
- Confirmation of candidate's identity

Ask the candidate if they're ready to begin and if they have any questions about the process.
""",
    completion_criteria="""
- Candidate has acknowledged they're ready
- Identity verification is complete
- Initial questions about process are addressed
""",
)

resume_review = InterviewPhase(
    name="Resume Review",
    instructions="""
You have access to [Candidate Name]'s resume and the job description for [Job Title]. Review the resume while considering the job requirements.

Generate questions that:
- Clarify gaps or transitions in their career history
- Explore their key responsibilities in relevant roles
- Validate their stated achievements
- Understand their career progression
- Connect their past experience to the current role

Important: Follow up on answers that need clarification or seem inconsistent with the resume. Focus particularly on experience related to [key job requirements].
""",
    completion_criteria="""
All major resume gaps/transitions are explained
Key experiences relevant to role are discussed
Responses about past roles align with resume claims
No major inconsistencies remain unexplored
    """,
)

technical_skills_assesment = InterviewPhase(
    name="Technical Skills Assessment",
    instructions="""
Based on the job description for [Job Title], assess the candidate's technical skills and expertise. You have their resume for context of their background.

Create questions that:
- Start with fundamental concepts in [required skill areas]
- Progressively increase in difficulty based on their responses
- Include scenario-based problems relevant to the role
- Allow candidates to demonstrate practical application of skills
- Validate claims of expertise from their resume

Adapt your questions based on their responses. If they struggle, simplify. If they excel, increase complexity.
""",
    completion_criteria="""
Core technical competencies are evaluated
Candidate has demonstrated proficiency level
Technical scenarios have been explored
Skills claimed on resume have been verified
""",
)


behavioral_assesment = InterviewPhase(
    name="Behavioral Assessment",
    instructions="""
As an AI interviewer, evaluate the candidate's behavioral competencies and soft skills relevant to [Job Title]. Use the STAR method (Situation, Task, Action, Result) to structure your questions.

Ask about:
- A challenging project they managed
- A conflict they resolved with a colleague
- A time they demonstrated [specific company value]
- Their approach to [relevant job challenge]

Follow up on vague answers with specific questions about their role, actions, and measurable outcomes. Look for alignment with [Company Name]'s values and culture.
""",
    completion_criteria="""
Required number of STAR scenarios completed
Key behavioral competencies assessed
Sufficient examples of relevant soft skills gathered
Company value alignment evaluated
""",
)


project_portfolio_discussion = InterviewPhase(
    name="Project Portfolio Discussion",
    instructions="""
Reference the projects mentioned in the candidate's resume. Create a detailed discussion about their most relevant work experience for [Job Title].

Ask about:
- Technical details of their most impressive project
- Their specific role and contributions
- Challenges faced and solutions implemented
- Results and impact of their work
- Learning experiences and growth

Probe deeper when answers are technical or implementation-focused to verify genuine expertise.
""",
    completion_criteria="""
Deep dive into at least one major project complete
Technical decision-making process understood
Impact and results validated
Learning/growth mindset assessed
""",
)

role_specific_questions = InterviewPhase(
    name="Role Specific Questions",
    instructions="""
Using the job description for [Job Title] at [Company Name], assess the candidate's understanding and preparation for this specific role.

Explore:
- Their understanding of the role's responsibilities
- How their experience prepares them for this position
- Their expected contribution in the first 6 months
- Their approach to [specific job challenge]
- Long-term career goals and alignment with this position

Look for specific, practical answers that demonstrate understanding of the role and company.
""",
    completion_criteria="""
Role understanding verified
Future goals alignment checked
Expected contributions discussed
Work style preferences understood
""",
)


candidate_questions = InterviewPhase(
    name="Candidate Questions",
    instructions="""
You represent [Company Name] as an AI interviewer. Your responses should be based on the approved company information provided.

When the candidate asks questions:
- Provide accurate, pre-approved information about the role and company
- If a question goes beyond your knowledge base, note it for human follow-up
- Be transparent about what you can and cannot answer
- Encourage questions about the role, team, and company culture

Stay within the scope of provided company information. Flag complex or sensitive questions for human follow-up.
""",
    completion_criteria="""
All questions addressed
Information about the role, team, and company culture provided
""",
)


closing = InterviewPhase(
    name="Closing",
    instructions="""
Conclude the interview professionally and clearly.

Your closing should:
- Summarize key points discussed
- Explain the next steps in the hiring process
- Provide timeline for feedback or next interview
- Thank the candidate for their time
- Ask if they have any final questions
- Confirm how they will be contacted with updates

Maintain a professional and positive tone while being clear about expectations and next steps.
""",
    completion_criteria="""
""",
)
# }}}


class Interviewer(ChatAgent):

    def __init__(self, company_name, job_title, job_description):
        super().__init__(
            name="Interviewer",
            description=f"AI interviewer for {job_title} at {company_name}",
            assistant=SimpleAssistant("You are an AI interviewer"),
        )
        self.company_name = company_name
        self.job_title = job_title
        self.job_description = job_description

        self.phases = [
            introduction,
            resume_review,
            technical_skills_assesment,
            behavioral_assesment,
            project_portfolio_discussion,
            role_specific_questions,
            candidate_questions,
            closing,
        ]
        self.current_phase = 0

    def message(self, input: str) -> Agent.Return:
        self.set_assistant()
        yield from super().message(input)

    def set_assistant(self):
        system_prompt = f"""
        You are an AI interviewer for {self.job_title} at {self.company_name}.

        There are several phases of the interview:
        - Introduction
        - Resume Review
        - Technical Skills Assessment
        - Behavioral Assessment
        - Project Portfolio Discussion
        - Role Specific Questions
        - Candidate Questions
        - Closing

        You are currently in the {self.phases[self.current_phase].name} phase.

        Here is your instructions:

        {self.phases[self.current_phase].instructions}

        Here is your completion criteria before moving to the next phase:

        {self.phases[self.current_phase].completion_criteria}
        """

        def mark_completed():
            print(f"Completed {self.phases[self.current_phase].name} phase.")
            self.current_phase += 1

        self.assistant = SimpleAssistant(system_prompt, [mark_completed])


interviewer = Interviewer(company_name, job_title, job_description)
