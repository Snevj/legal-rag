from dataclasses import dataclass


@dataclass
class EvalCase:
    question: str
    reference_answer: str
    expected_doc_id: str


EVAL_DATASET: list[EvalCase] = [
    EvalCase(
        question="What year was Marbury v. Madison decided?",
        reference_answer="Marbury v. Madison was decided in 1803.",
        expected_doc_id="marbury_v_madison",
    ),
    EvalCase(
        question="Who delivered the opinion of the court in Marbury v. Madison?",
        reference_answer="Chief Justice Marshall delivered the opinion of the court.",
        expected_doc_id="marbury_v_madison",
    ),
    EvalCase(
        question="What did Marbury seek from the court?",
        reference_answer=(
            "Marbury sought a writ of mandamus compelling the Secretary of State to "
            "deliver his commission as a justice of the peace."
        ),
        expected_doc_id="marbury_v_madison",
    ),
    EvalCase(
        question="What year was Brown v. Board of Education decided?",
        reference_answer="Brown v. Board of Education was decided in 1954.",
        expected_doc_id="brown_v_board_of_education",
    ),
    EvalCase(
        question="What was the central legal question in Brown v. Board of Education?",
        reference_answer=(
            "Whether racial segregation in public schools, even with substantially "
            "equal facilities, violates the Equal Protection Clause of the Fourteenth "
            "Amendment."
        ),
        expected_doc_id="brown_v_board_of_education",
    ),
    EvalCase(
        question="What did Brown v. Board of Education hold about 'separate but equal' in public education?",
        reference_answer=(
            "The Court held that separate educational facilities are inherently "
            "unequal and therefore unconstitutional in public education."
        ),
        expected_doc_id="brown_v_board_of_education",
    ),
    EvalCase(
        question="What year was Gideon v. Wainwright decided?",
        reference_answer="Gideon v. Wainwright was decided in 1963.",
        expected_doc_id="gideon_v_wainwright",
    ),
    EvalCase(
        question="What constitutional right did Gideon v. Wainwright establish for criminal defendants?",
        reference_answer=(
            "The right to court-appointed counsel for indigent defendants in state "
            "criminal trials, under the Sixth Amendment as applied to the states."
        ),
        expected_doc_id="gideon_v_wainwright",
    ),
    EvalCase(
        question="What year was Miranda v. Arizona decided?",
        reference_answer="Miranda v. Arizona was decided in 1966.",
        expected_doc_id="miranda_v_arizona",
    ),
    EvalCase(
        question="What warnings must police give a suspect before custodial interrogation under Miranda v. Arizona?",
        reference_answer=(
            "That the suspect has the right to remain silent, that anything said can "
            "be used against them in court, that they have the right to an attorney, "
            "and that an attorney will be appointed if they cannot afford one."
        ),
        expected_doc_id="miranda_v_arizona",
    ),
    EvalCase(
        question="What year was Tinker v. Des Moines decided?",
        reference_answer="Tinker v. Des Moines was decided in 1969.",
        expected_doc_id="tinker_v_des_moines",
    ),
    EvalCase(
        question="What did Tinker v. Des Moines hold about students' First Amendment rights in public schools?",
        reference_answer=(
            "Students do not shed their constitutional rights to freedom of speech at "
            "the schoolhouse gate, and symbolic speech like wearing armbands is "
            "protected unless it substantially disrupts school activities."
        ),
        expected_doc_id="tinker_v_des_moines",
    ),
]
