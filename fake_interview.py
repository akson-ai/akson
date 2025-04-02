from dotenv import load_dotenv

load_dotenv()

from agents.interviewer import company_name
from agents.interviewer import interviewer as agent
from agents.interviewer import job_description, job_title
from framework import ConversationalAgent, DeclarativeAssistant

# {{{ input
resume = """
# Cenk Alti
Contact: <cenk@alti.email>

## Summary
I am a software engineer with 10+ years experience in web application development and deployment.
I like solving hard problems to make apps more performant, reliable and secure
while focusing on simplicity, testing and standards based design.

## Technical Skills
- Go, Python, C
- MySQL, Redis, RabbitMQ, Etcd
- NGINX, uWSGI, Flask
- Nagios, Jenkins, Salt, Docker, ffmpeg

## Professional Experience

### [Atolio](https://atolio.com): Senior Backend Engineer, Toronto, 01/2024-07/2024
Enterprise internal search platform

- Developing and maintaining the connector SDK for Atolio's search product.
- Managing internal and external connector development.

### [AWS](https://aws.amazon.com): Software Development Engineer, Toronto, 09/2021-06/2023

- In [EKS](https://aws.amazon.com/eks/) team, I improved availability and performance of [etcd](https://github.com/etcd-io/etcd) clusters.
- In [RDS](https://aws.amazon.com/rds/) team, I worked on a project to scale Aurora MySQL to 1000s of nodes.

### [Amazon](https://amazon.com): Software Development Engineer, Toronto, 12/2020-09/2021
- In Customer Service Tech team, I worked on scheduling tools for customer service agents.

### [Put.io](https://put.io): Software Engineer, Istanbul, 12/2015-10/2020
Cloud storage service

- Designed and developed a BitTorrent client: [Rain](https://github.com/cenkalti/rain)
- Wrote a payment gateway for accepting NANO: [Accept Nano](https://accept-nano.com/)
- Replaced MogileFS with in-house developed filesystem: [Efes](https://github.com/putdotio/efes/)
- Migrated codebase from Python 2 to 3
- Helped containerization of the application and migration to ECS

### [Koding.com](https://koding.com): Software Engineer, Remote, 10/2013-04/2014
Cloud based development environment

- Worked on distributed micro-service framework in Go: [Kite](https://github.com/koding/kite)

### [Put.io](https://put.io): Software Engineer, Istanbul, 03/2011-10/2013
Cloud storage service

- Implemented a task queue in Python: [Kuyruk](https://kuyruk.readthedocs.io)
- Implemented continuous integration/deployment
- Lead the migration of PHP codebase to Python
- Wrote the new version of the public API
- Managed storage and download servers

## Education

### Information Systems Engineering B.Sc., 2005-2010
Dual diploma program

- [SUNY Binghamton University](https://www.binghamton.edu) (Binghamton, NY)
- [Bogazici University](https://boun.edu.tr/) (Istanbul, Turkey)
"""
# }}}


class Interviewee(DeclarativeAssistant):
    """You are a user agent that helps users to chat with Interviewer.

    You're applying for a job at {company_name} as a {job_title}.

    Chat with the interviewer about the job you are applying for.
    Answer interviewer's questions about the job and your resume.
    If you don't know the answer, make it up.

    <job_description>
    {job_description}
    </job_description>

    <resume>
    {resume}
    </resume>
    """

    def __init__(self, company_name, job_title, job_description, resume):
        super().__init__()
        self.system_prompt = self.system_prompt.format(
            company_name=company_name,
            job_title=job_title,
            job_description=job_description,
            resume=resume,
        )
        self.finished = False

    def mark_finished(self):
        """Call this function when the interview is finished."""
        self.finished = True


user = ConversationalAgent(
    name="Interviewee",
    description="A user agent that helps users to chat with Interviewer.",
    assistant=Interviewee(
        company_name=company_name,
        job_title=job_title,
        job_description=job_description,
        resume=resume,
    ),
)


user_message = ""
while not user.assistant.finished:  # type: ignore
    agent_message = next(agent.message(user_message))
    assert isinstance(agent_message, str)
    print(f"Agent: {agent_message}")
    print("-" * 80)
    user_message = next(user.message(agent_message))
    assert isinstance(user_message, str)
    print(f"User: {user_message}")
    print("-" * 80)
