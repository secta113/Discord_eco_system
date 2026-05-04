import random
from typing import Dict, List, Optional, Tuple

from logic.dobumon.core.dob_exceptions import DobumonError, DobumonGeneticsError
from logic.dobumon.genetics.dob_genetics_constants import GeneticConstants


class MutationEngine:
    """
    突然変異の発生、遺伝子座の固定（ホモ接合化）を管理するエンジンクラス。
    """

    # 特定の形質が発現した際に、その遺伝子座を固定（Fixation）するルール。
    # 旧 GeneticFixer からの移行。
    FIX_RULES: Dict[str, str] = {
        "anti_taboo": "potential",
        "singularity": "potential",
        "antinomy": "potential",
    }

    @classmethod
    def generate_random_mutation(cls) -> Tuple[str, str]:
        """
        MUTATION_GENE_POOL からランダムに1つの突然変異（遺伝子座, アレル）を選択します。
        """
        all_pool_mutations = []
        for slot, alleles in GeneticConstants.MUTATION_GENE_POOL.items():
            for a in alleles:
                all_pool_mutations.append((slot, a))

        if not all_pool_mutations:
            raise DobumonGeneticsError("MUTATION_GENE_POOL is empty.")

        return random.choice(all_pool_mutations)

    @classmethod
    def apply_mutation(
        cls,
        genotype: Dict[str, List[str]],
        allele: Optional[str] = None,
        slot: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        指定された、あるいはランダムな突然変異を遺伝子型に適用します。
        強力な変異の場合は、自動的にホモ接合化（固定）を行います。

        Args:
            genotype: 修正対象の遺伝子型
            allele: 適用するアレル（None の場合はランダム）
            slot: 適用する遺伝子座（None の場合はランダム、allele 指定時はそれに合わせる）

        Returns:
            Dict[str, List[str]]: 修正後の遺伝子型（インプレースでも修正されます）
        """
        if allele is None:
            # アレルもスロットも未指定ならランダムに決定
            slot, allele = cls.generate_random_mutation()
        elif slot is None:
            # アレルのみ指定されている場合、そのアレルが属するスロットを探す
            for s, pool in GeneticConstants.MUTATION_GENE_POOL.items():
                if allele in pool:
                    slot = s
                    break
            if slot is None:
                # どのプールにも存在しないアレルの場合はエラー
                raise DobumonGeneticsError(f"Unknown mutation allele: {allele}")

        if allele in cls.FIX_RULES:
            # 強力な変異（固定ルール対象）の場合、両方の座を書き換える
            genotype[slot] = [allele, allele]
        else:
            # 通常の突然変異。元のペアのどちらかを置換する（結果的に D か r が残る）
            idx = random.randint(0, 1)
            genotype[slot][idx] = allele

        return genotype

    @classmethod
    def fixate_genotype(cls, genotype: Dict[str, List[str]], active_traits: List[str]):
        """
        発現している特性に基づいて遺伝子型をインプレースで修正（ホモ接合化）します。
        旧 GeneticFixer.fixate_genotype の移植。
        """
        for trait, locus in cls.FIX_RULES.items():
            if trait in active_traits and locus in genotype:
                # 100% 遺伝を保証するため、その形質自体をアレルとして両方の座にセットします。
                genotype[locus] = [trait, trait]
