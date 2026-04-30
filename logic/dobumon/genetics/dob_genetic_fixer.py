from typing import Dict, List


class GeneticFixer:
    """
    特定の形質が発現した際に、その遺伝子座をホモ接合（Homogeneous pair）に書き換えて固定（Fixation）するロジックを提供します。
    これにより、次世代への 100% 遺伝を保証します。
    """

    # 形質名と、それが属する遺伝子座（locus）のマッピング。
    # ここに定義された形質が発現している（traitsに含まれる）場合、対応する遺伝子座がその形質のペアに書き換えられます。
    FIX_RULES: Dict[str, str] = {
        "anti_taboo": "potential",
        "singularity": "potential",
        "antinomy": "potential",
    }

    @classmethod
    def fixate_genotype(cls, genotype: Dict[str, List[str]], active_traits: List[str]):
        """
        発現している特性に基づいて遺伝子型をインプレースで修正します。
        """
        for trait, locus in cls.FIX_RULES.items():
            if trait in active_traits and locus in genotype:
                # 100% 遺伝を保証するため、その形質自体をアレルとして両方の座にセットします。
                genotype[locus] = [trait, trait]
