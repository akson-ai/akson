from framework import Agent, ConversationalAgent, SimpleAssistant

# {{{ input
company_name = """Uniquetech"""

job_title = """Plant Manager"""

job_description = """
     # Plant Manager - Metal Machining Factory

## Position Overview
We are seeking an experienced Plant Manager to oversee all operations at our metal machining facility. The ideal candidate will combine technical expertise in metal manufacturing with strong leadership abilities to drive operational excellence, ensure quality standards, and maintain a safe working environment.

## Key Responsibilities

### Operations Management
- Direct daily manufacturing operations, including CNC machining, metal fabrication, and assembly processes
- Optimize production schedules and workflows to maximize efficiency and meet customer deadlines
- Implement and maintain lean manufacturing principles and continuous improvement initiatives
- Monitor and analyze production metrics, quality indicators, and operational KPIs
- Develop and manage annual operating budgets and capital expenditure plans

### Quality and Safety
- Ensure compliance with ISO 9001 quality management systems and industry standards
- Maintain OSHA safety standards and promote a zero-incident safety culture
- Lead quality improvement initiatives and implement corrective actions as needed
- Oversee preventive maintenance programs for all machinery and equipment
- Ensure proper documentation of all quality and safety procedures

### Team Leadership
- Manage a team of 50-100 employees across multiple shifts
- Recruit, train, and develop production supervisors and technical staff
- Conduct regular performance evaluations and implement development plans
- Foster a culture of accountability, innovation, and continuous learning
- Address employee relations issues and maintain positive workforce morale

### Strategic Planning
- Collaborate with senior management to develop and execute business strategies
- Identify opportunities for process improvements and cost reduction
- Lead capacity planning initiatives and equipment acquisition projects
- Develop contingency plans for potential operational disruptions
- Drive innovation in manufacturing processes and technology adoption

## Required Qualifications
- Bachelor's degree in Manufacturing Engineering, Mechanical Engineering, or related field
- 10+ years of progressive experience in manufacturing, with at least 5 years in a leadership role
- Extensive knowledge of metal machining processes, CNC programming, and tooling
- Strong understanding of lean manufacturing principles and Six Sigma methodologies
- Proven track record of implementing operational improvements and cost reduction initiatives
- Experience with ERP systems and production planning software
- Excellent problem-solving and analytical skills
- Outstanding leadership and communication abilities

## Preferred Qualifications
- Master's degree in Engineering or Business Administration
- Professional certifications (PE, PMP, Six Sigma Black Belt)
- Experience with automation and robotics integration
- Knowledge of ISO 9001 and AS9100 quality management systems
- Multilingual capabilities (Turkish/English required)

## Physical Requirements
- Ability to walk and stand for extended periods
- Capability to access all areas of the manufacturing facility
- Must be able to wear required PPE (safety glasses, steel-toe boots, hearing protection)
- Occasional lifting up to 25 pounds

## Working Conditions
- Full-time position with occasional evening and weekend availability required
- Climate-controlled manufacturing environment
- Exposure to typical machine shop conditions (noise, metal chips, cutting fluids)
- Travel up to 15% for vendor/customer visits and corporate meetings

## Benefits
- Competitive salary commensurate with experience
- Comprehensive health, dental, and vision insurance
- 401(k) with company match
- Performance-based bonus program
- Professional development and training opportunities
- Paid time off and holidays
- Life and disability insurance

## Reports To
Director of Manufacturing

## Location
Bursa, Turkey

Qualified candidates should submit their resume, cover letter, and references to [email/application portal].

Uniquetech is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, sexual orientation, gender identity, national origin, disability, or veteran status.
"""

resume = """
# Ayhan Bestepe - CV

## Contact Information
- **Phone:** (555) 560 38 28
- **Email:** ayhanbestepe@gmail.com
- **Location:** Nilüfer - Bursa, Turkey
- **Nationality:** Turkish
- **Marital Status:** Married
- **Driver’s License:** B

---

## Education
- **PhD in Advanced Technologies and Material Science**
  Bursa Teknik Üniversitesi (GPA 4.00/4.00)
  Thesis: Preparation and Electrochemical Performance Effects of Rare Earth Element-Doped NMC Cathode Materials in Lithium-Ion Batteries

- **MSc in Automotive Engineering**
  Boğaziçi Üniversitesi
  Thesis: Performance Optimization of Lithium-Ion Batteries through Process Changes

- **BA in Business Administration**
  Anadolu Üniversitesi

- **BSc in Mechanical Engineering**
  Yeditepe Üniversitesi
  Thesis: Design and Transmission Analysis of an Unmanned Hovercraft

- **Exchange Student in Mechanical Engineering**
  Vaxjö University, Sweden

---

## Expertise
- Powertrain Components, Lithium-Ion Batteries, Magnets, Electric Motors, Powder Metallurgy

---

## Languages
- **Turkish:** Native
- **English:** Advanced
- **Japanese & German:** Beginner

---

## Technical Skills
- **General Software:** Word, Excel, PowerPoint, WebEx, TeamCenter
- **Modeling Tools:** Catia, SolidWorks, AutoCAD, VisMockup
- **Analysis Tools:** STAR CCM+, ANSYS
- **Programming Languages:** VBA, C#
- **Other:** Unity, Photoshop, Sharepoint, Oracle

---

## Professional Experience

### UNIQUETECH Muhendislik (2022 - Present)
**Deputy General Manager**

### Makine ve Kimya Endüstrisi (2021 - 2022)
**General Manager Consultant**
- Directed R&D for weaponry, ammunition, mechatronics, rockets, explosives, and chemicals across 11 factories.

### TÜBİTAK (TÜSSİDE) (2020 - 2021)
**Technical Consultant**
- Conducted feasibility studies for rare earth elements and magnet production.

### Rumelisiad Girişim A.Ş. (2018 - 2020)
**General Manager**
- Focused on high-purity silicon, lithium-ion batteries, electric motors, and magnets.

### Doğu Pres Otomotiv (2017 - 2018)
**R&D Director**

### Toyota Boshoku Europe N.V. (2010 - 2017)
- **R&D Filter and Powertrain Division - Assistant Manager**
  - Led projects for filtration and powertrain components, including Li-ion batteries and electric motors.
- **VA/VE Division - Assistant Manager**
  - Cost-reduction activities across multiple factories in Europe, Africa, and the Middle East.

### Ford Otosan (2007 - 2010)
- **Powertrain Division - Senior Air Intake Systems Engineer**
- **Powertrain Division - Driveline Engineer**

---

## Selected Projects
- Preparation of Rare Earth-Doped NMC Cathode Materials for Li-Ion Batteries
- Lithium-Ion Batteries: Process Changes for Performance Optimization
- Air Intake Design for Ford Galaxy, S-Max, Edge, and Mondeo
- Driveline System Design of Cargo Trucks
- Feasibility Study System (VBA software)

---

## Certifications
- Six Sigma Green Belt
- CATIA Professional Designer
- ANSYS Workbench
- NVH (Basics of Vibration)
- Toyota Way & Problem Solving

---

## Laboratory Experience
- SEM & FIB (EDX, EBSD, WDS Detectors)
- XRD, ICP-OES, Particle Sizer, Ion Mill
- Battery Aging Chambers, Electrode Slurry Production

---

## Conferences & Workshops
- SEDEC 2022, Ankara (Speaker)
- Rare Earth Elements Workshop, Kırka (Speaker)
- Technology Networks for Rare Earth and Refractory Metals, Ankara

---

## Hobbies
- Technology advancements, reading about automotive engineering, and research on renewable energy.
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


class Interviewer(ConversationalAgent):

    def __init__(self, company_name, job_title, job_description, resume):
        super().__init__(
            name="Interviewer",
            description=f"AI interviewer for {job_title} at {company_name}",
            assistant=SimpleAssistant("You are an AI interviewer"),
        )
        self.company_name = company_name
        self.job_title = job_title
        self.job_description = job_description
        self.resume = resume

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

        <job_description>
        {self.job_description}
        </job_description>

        <resume>
        {self.resume}
        </resume>
        """

        def mark_completed():
            print(f"Completed {self.phases[self.current_phase].name} phase.")
            self.current_phase += 1

        self.assistant = SimpleAssistant(system_prompt, [mark_completed])


interviewer = Interviewer(company_name, job_title, job_description, resume)
