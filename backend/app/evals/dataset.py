from dataclasses import dataclass


@dataclass
class EvalCase:
    question: str
    reference_answer: str
    expected_doc_id: str


EVAL_DATASET: list[EvalCase] = [
    EvalCase(
        question="What year was Kesavananda Bharati v. State of Kerala decided?",
        reference_answer="Kesavananda Bharati v. State of Kerala was decided in 1973.",
        expected_doc_id="kesavananda_bharati_v_state_of_kerala",
    ),
    EvalCase(
        question="What doctrine did Kesavananda Bharati v. State of Kerala establish?",
        reference_answer=(
            "The Basic Structure Doctrine: Parliament's power to amend the "
            "Constitution under Article 368 does not extend to altering its basic "
            "structure or essential features."
        ),
        expected_doc_id="kesavananda_bharati_v_state_of_kerala",
    ),
    EvalCase(
        question="How large was the bench that decided Kesavananda Bharati v. State of Kerala?",
        reference_answer=(
            "A 13-judge bench, the largest in the history of the Supreme Court of "
            "India, decided the case by a 7-6 majority."
        ),
        expected_doc_id="kesavananda_bharati_v_state_of_kerala",
    ),
    EvalCase(
        question="What year was Maneka Gandhi v. Union of India decided?",
        reference_answer="Maneka Gandhi v. Union of India was decided in 1978.",
        expected_doc_id="maneka_gandhi_v_union_of_india",
    ),
    EvalCase(
        question="What did Maneka Gandhi v. Union of India hold about 'procedure established by law' under Article 21?",
        reference_answer=(
            "That the procedure must be fair, just, and reasonable, not arbitrary "
            "or oppressive - expanding Article 21 and linking it with Articles 14 "
            "and 19."
        ),
        expected_doc_id="maneka_gandhi_v_union_of_india",
    ),
    EvalCase(
        question="What year was Vishaka v. State of Rajasthan decided?",
        reference_answer="Vishaka v. State of Rajasthan was decided in 1997.",
        expected_doc_id="vishaka_v_state_of_rajasthan",
    ),
    EvalCase(
        question="What did Vishaka v. State of Rajasthan establish, in the absence of specific legislation?",
        reference_answer=(
            "Guidelines (the Vishaka Guidelines) to prevent and address sexual "
            "harassment of women at the workplace, later codified into the "
            "Sexual Harassment of Women at Workplace (POSH) Act, 2013."
        ),
        expected_doc_id="vishaka_v_state_of_rajasthan",
    ),
    EvalCase(
        question="What year was the Puttaswamy Aadhaar judgment decided?",
        reference_answer="Justice K.S. Puttaswamy (Retd.) v. Union of India (the Aadhaar case) was decided in 2018.",
        expected_doc_id="puttaswamy_v_union_of_india",
    ),
    EvalCase(
        question="What did the Supreme Court hold about the constitutional validity of the Aadhaar Act in Puttaswamy v. Union of India?",
        reference_answer=(
            "The Court upheld the constitutional validity of the Aadhaar Act, 2016 "
            "by a 4:1 majority, while striking down certain provisions including "
            "Section 57, which had allowed private entities to use Aadhaar "
            "authentication."
        ),
        expected_doc_id="puttaswamy_v_union_of_india",
    ),
    EvalCase(
        question="What year was Shreya Singhal v. Union of India decided?",
        reference_answer="Shreya Singhal v. Union of India was decided in 2015.",
        expected_doc_id="shreya_singhal_v_union_of_india",
    ),
    EvalCase(
        question="What did Shreya Singhal v. Union of India hold about Section 66A of the Information Technology Act?",
        reference_answer=(
            "The Court struck down Section 66A of the Information Technology Act, "
            "2000 as unconstitutional, holding it violated the freedom of speech "
            "and expression under Article 19(1)(a) and was not saved by the "
            "reasonable restrictions in Article 19(2)."
        ),
        expected_doc_id="shreya_singhal_v_union_of_india",
    ),
]
