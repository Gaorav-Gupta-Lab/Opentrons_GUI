
"""
Dennis A Simpson
University of North Carolina at Chapel Hill
450 West Drive
Chapel Hill, NC  27599
"""

import sys
from packaging.version import Version
from collections import defaultdict
from Utilities import parse_sample_template, calculate_volumes, plate_layout

__version__ = "4.1.0"
__author__ = "Dennis A. Simpson"
__copyright__ = "Copyright 2025, University of North Carolina at Chapel Hill"
__license__ = "MIT"
__email__ = "dennis@email.unc.edu"
__status__ = "Development"


class TemplateErrorChecking:
    def __init__(self, input_file):
        self.stdout = sys.stdout
        self.sample_dictionary, self.args = parse_sample_template(input_file)
        self.pipette_info_dict = {
            "p20_single_gen2": ["opentrons_96_tiprack_20ul", "opentrons_96_filtertiprack_20ul"],
            "p300_single_gen2": ["opentrons_96_tiprack_300ul", "opentrons_96_filtertiprack_200ul"]
            }
        self.slot_dict = None
        self.left_tip_boxes = []
        self.right_tip_boxes = []
        self.max_template_vol = None
        self.LeftPipette = "p300_single_gen2"
        self.RightPipette = "p20_single_gen2"
        self.labware_slot_definitions = [
            "vwrscrewcapcentrifugetube5ml_15_tuberack_5000ul", "opentrons_15_tuberack_5000ul_diamond_tubes",
            "opentrons_24_tube_rack_vwr_microfuge_tube_1.5ml",
            "screwcap_24_tuberack_500ul", "opentrons_24_tuberack_generic_2ml_screwcap",
            "bigwell_96_tuberack_200ul_dilution_tube", "8_well_strip_tubes_200ul",
            "biorad_ddpcr_plate_aluminum_block_100ul", "biorad_hardshell_96_wellplate_150ul",
            "eppendorftwin.tecpcrplates_96_aluminumblock_150ul",
            "parhelia_temp_module_with_biorad_ddpcr_plate_100ul", "parhelia_temp_module_with_twintec_ddpcr_plate_150ul",
            "opentrons_96_tiprack_20ul", "opentrons_96_filtertiprack_20ul",
            "opentrons_96_tiprack_300ul", "opentrons_96_filtertiprack_200ul",
            "stacked_vwr_96_well_semi_skirt_96_well_plate_200ul", "stacked_eppendorf_twin.tec_pcr_96_well_plate_200ul"
            ]

        self.tip_boxes = ["opentrons_96_tiprack_20ul", "opentrons_96_filtertiprack_20ul",
                          "opentrons_96_tiprack_300ul", "opentrons_96_filtertiprack_200ul"
                          ]

        self.well_label_dict = self.well_labels()

    def parameter_checks(self):
        """
        Make sure various parameters that are common to all setups exist in the parameter template.
        :return:
        """

        msg = ""
        if not self.args.PCR_Volume:
            msg += "--PCR_Volume is not defined.\n"
        if self.args.Template.strip() == "Illumina_Dual_Indexing":
            if not self.args.TotalReagentVolume:
                msg += "--TotalReagentVolume is not defined.\n"
            if not self.args.DNA_in_Reaction:
                msg += "--DNA_in_Reaction is not defined"
        if not self.args.WaterResVol:
            msg += "--WaterResVol is not defined.\n"
        if not self.args.WaterResWell:
            msg += "--WaterResWell is not defined.\n"
        if not self.args.ReagentSlot:
            msg += "--ReagentSlot is not defined.\n"
        if not self.args.PCR_PlateSlot:
            msg += "--PCR_PlateSlot is not defined.\n"
        if not self.args.BottomOffset:
            msg += "--BottomOffset is not defined.\n"
        if not self.args.LeftPipetteFirstTip:
            msg += "--LeftPipetteFirstTip is not defined.\n"
        if not self.args.RightPipetteFirstTip:
            msg += "--RightPipetteFirstTip is not defined.\n"
        if not self.args.User:
            msg += "--User name is missing from template.\n"

        return msg

    def slot_error_check(self):
        """
        Make sure the slots contain valid labware definitions and check for inappropriate labware such as a pipette
        tip box in the defined reagent slot.
        :return:
        """
        print("Checking Labware Definitions in Slots")
        slot_error = ""
        slot_list = \
            ["Slot1", "Slot2", "Slot3", "Slot4", "Slot5", "Slot6", "Slot7", "Slot8", "Slot9", "Slot10", "Slot11"]

        slot_dict = {}
        for i in range(len(slot_list)):
            labware = getattr(self.args, "{}".format(slot_list[i]))

            if labware and labware not in self.labware_slot_definitions:
                slot_error = ("ERROR: Slot {}, labware definition \"{}\" is not valid.\nCheck spelling."
                       .format(i+1, labware))

            elif labware and i+1 == int(self.args.ReagentSlot) and labware in self.tip_boxes:
                slot_error = "ERROR: --ReagentSlot contains a tip box."

            elif labware and i+1 == int(self.args.PCR_PlateSlot) and labware in self.tip_boxes:
                slot_error = "ERROR: --PCR_PlateSlot contains a tip box."

            elif labware:
                slot_dict[str(i + 1)] = labware

        if slot_error:
            print("NOTICE: There are errors in the labware definitions.  Correct these and run again\n")
        else:
            print("\tLabware definitions in slots passed")

        self.slot_dict = slot_dict

        try:
            self.slot_dict[self.args.PCR_PlateSlot]
        except KeyError:
            return "--PCR_PlateSlot {} has no labware defined".format(self.args.PCR_PlateSlot)

        self.tip_box_error_check()
        return slot_error

    def pipette_error_check(self):
        """
        This will check if the pipette definition given in the template file is proper.  It will not check if these
        match what is actually installed on the robot.
        :return:
        """
        msg = ""
        pipette_error = False
        print("Checking Pipette Definitions")

        if self.LeftPipette:
            if self.pipette_definition_error_check(pipette_error, self.LeftPipette, "Left Pipette"):
                msg = "The Left Pipette definition {} is not valid\n".format(self.LeftPipette)
        if self.RightPipette:
            if self.pipette_definition_error_check(pipette_error, self.RightPipette, "Right Pipette"):
                msg += "The Right Pipette definition {} is not valid\n".format(self.RightPipette)
        if not msg:
            print("\tPipette definitions passed.")

        return msg

    def tip_box_error_check(self):
        for slot in self.slot_dict:
            labware = self.slot_dict[slot]
            lft_pipette_labware = self.pipette_info_dict[self.LeftPipette]
            rt_pipette_labware = self.pipette_info_dict[self.RightPipette]
            if labware in lft_pipette_labware and slot not in self.left_tip_boxes:
                self.left_tip_boxes.append(slot)
            elif labware in rt_pipette_labware and slot not in self.right_tip_boxes:
                self.right_tip_boxes.append(slot)

        return

    def slot_usage_error_check(self, labware, type_check):
        """
        Check that labware in slots is appropriate for program being executed.
        :param labware:
        :param type_check:
        :return:
        """
        msg = ""
        # Check the Slot definitions
        if not labware:
            msg = '{} Slot Labware definition missing in template.'.format(type_check)
            print("ERROR: {}".format(msg))
        else:
            for pipette in self.pipette_info_dict:
                if labware in self.pipette_info_dict[pipette]:
                    print(labware, self.pipette_info_dict[pipette])
                    msg = "{} slot contains a pipette tip box".format(type_check)
                    print("ERROR: {}".format(msg))

        return msg

    def dispense_samples(self, sample_data_dict, water_aspirated, p20_tips_used, p300_tips_used):
        """
        @param sample_data_dict:
        @param water_aspirated:
        @param p20_tips_used:
        @param p300_tips_used:
        """

        sample_parameters = self.sample_dictionary

        for sample_key in sample_parameters:
            sample_dest_wells = sample_data_dict[sample_key][3]
            sample_vol = sample_data_dict[sample_key][0]
            diluent_vol = sample_data_dict[sample_key][1]
            diluted_sample_vol = sample_data_dict[sample_key][2]

            # If no dilution is necessary, dispense sample and continue
            if diluted_sample_vol == 0:
                if sample_vol <= 20:
                    p20_tips_used += 1
                else:
                    p300_tips_used += 1
                continue

            # Adjust volume of diluted sample to make sure there is enough
            diluted_template_needed = diluted_sample_vol * (len(sample_dest_wells) + 1)
            diluted_template_on_hand = sample_vol + diluent_vol
            diluted_template_factor = 1.0
            if diluted_template_needed <= diluted_template_on_hand:
                diluted_template_factor = diluted_template_needed / diluted_template_on_hand
                if diluted_template_factor <= 1.5 and (sample_vol * diluted_template_factor) < 10:
                    diluted_template_factor = 2.0

            diluent_vol = diluent_vol * diluted_template_factor
            if diluted_sample_vol <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1

            if (sample_vol*diluted_template_factor) <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1

            if diluent_vol <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1

            water_aspirated += diluent_vol
        return water_aspirated, p20_tips_used, p300_tips_used

    def pcr_targets(self):
        """
        Parse Targets and check for errors
        :return:
        """
        target_count = 0
        no_target_count = 0
        msg = ""
        for i in range(10):
            target = getattr(self.args, "Target_{}".format(i+1))
            if target:
                if all('' == s or s.isspace() for s in target):
                    no_target_count += 1
                else:
                    target_count += 1
                    if not target[0]:
                        msg += "{} Well definition is missing".format(target[i])
                    if target[0] == self.args.WaterResWell.upper():
                        msg += "{} Target Well definition is the same as the --WaterResWell".format(target[i])
                    if not target[1]:
                        msg += "{} Target Name definition is missing".format(target[i])
                    if not target[2]:
                        msg += "{} Target Volume definition is missing".format(target[i])

        if no_target_count == 10:
            msg = "No targets defined"

        return target_count, msg

    def pcr_check(self, template):
        """
        Test ddPCR and Generic PCR templates.
        type template: object
        :param template:
        :return:
        :rtype: object
        """

        # Make sure user has provided the correct template version.
        if "ddPCR" in self.args.Template and Version(self.args.Version) < Version("3.0.1"):
            return ("{} Parameter Template Version is {}.\nTemplate Version Must Be >= 3.0.1\n"
                    .format(template, self.args.Version))
        elif "Generic PCR" in self.args.Template and Version(self.args.Version) < Version("3.0.1"):
            return ("{} Parameter Template Version is {}.\nTemplate Version Must Be >= 3.0.1\n"
                    .format(template, self.args.Version))

        if self.args.ReagentSlot:
            try:
                reagent_labware = self.slot_dict[self.args.ReagentSlot]
            except KeyError:
                return "--ReagentSlot {} has no labware defined".format(self.args.ReagentSlot)

        self.max_template_vol = round(float(self.args.PCR_Volume) - float(self.args.MasterMixPerRxn), ndigits=1)
        msg = self.slot_usage_error_check(reagent_labware, type_check="Reagent")

        if msg:
            return msg

        if self.args.Template.strip() != "Illumina_Dual_Indexing":
            target_count, msg = self.pcr_targets()
        else:
            target_count = 1

        if msg:
            return msg

        sample_data_dict, water_well_dict, target_well_dict, used_wells, layout_data, msg = \
            self.sample_processing()

        if msg:
            return msg

        p20_tips_used = 0
        p300_tips_used = 0
        water_aspirated = 0

        for well in water_well_dict:
            # Currently I am using distribute for the water.  That is 1 p300 tip
            water_aspirated += water_well_dict[well]
            """
            if water_vol <= 20:
                # p20_tips_used += 1
                p20_tips_used = 1
            else:
                # p300_tips_used += 1
                p300_tips_used = 1
            water_aspirated += water_vol
            """

        target_well_count = 0
        for target in target_well_dict:
            # Force user to include extra reagent in tube to account for pipetting errors
            reagent_used = float(self.args.MasterMixPerRxn) * 1.20

            # Get information about the master mix
            if self.args.Template.strip() != "Illumina_Dual_Indexing":
                target_info = getattr(self.args, "Target_{}".format(target))
                reagent_well_vol = float(target_info[2])
                reagent_name = "Target {}".format(target_info[1])
            else:
                reagent_well_vol = float(self.args.TotalReagentVolume)
                reagent_name = "Indexing Master Mix"

            # How much master mix per reaction?
            reagent_aspirated = float(self.args.MasterMixPerRxn)
            target_well_list = target_well_dict[target]

            # Currently using a distribute function.
            p300_tips_used += target_count
            if self.args.Template.strip() != "Illumina_Dual_Indexing":
                reagent_used += reagent_aspirated*len(target_well_list)
            else:
                # Add 5% to volume
                reagent_used = (len(used_wells)*float(self.args.MasterMixPerRxn))*1.05

            # Add a reagent tips for the no template control
            if float(self.args.PCR_Volume)-reagent_aspirated <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1

            target_well_count += len(target_well_list)

            if reagent_used >= reagent_well_vol:
                msg = "Program requires minimum of {} uL of {}.  You have {} uL."\
                      .format(reagent_used, reagent_name, reagent_well_vol)
                return msg

        water_aspirated, p20_tips_used, p300_tips_used = \
            self.dispense_samples(sample_data_dict, water_aspirated, p20_tips_used, p300_tips_used)

        if target_well_count == 0:
            return "Number of wells containing targets is 0.  Check TSV file for errors in sample table."
        if self.args.Template.strip() != "Illumina_Dual_Indexing":
            water_aspirated, p20_tips_used, p300_tips_used = \
                self.empty_well_vol(plate_layout(self.slot_dict[self.args.PCR_PlateSlot]), target_well_count,
                                    p20_tips_used, p300_tips_used, water_aspirated)
        else:
            p300_tips_used = 2
            p20_tips_used = (len(used_wells)*3)+4

        # Check Water Volume
        if int(self.args.WaterResVol) <= water_aspirated:
            msg = "Program requires minimum of {} uL water.  You have {} uL."\
                .format(round(water_aspirated, 0), self.args.WaterResVol)
            return msg

        # Check if there are enough tips
        msg = self.available_tips(p20_tips_used, p300_tips_used)

        if msg:
            return msg

    def available_tips(self, p20_tips_used, p300_tips_used):
        right_tips_used = p20_tips_used
        left_tips_used = p300_tips_used

        msg = ""
        tip_box_layout, layout_list = plate_layout(labware="96-TipBox")
        try:
            left_available = \
                (len(self.left_tip_boxes)*96)-tip_box_layout.index(self.args.LeftPipetteFirstTip.upper())
        except ValueError:
            msg += "Starting tip definition {} for Left Pipette is not valid\n".format(self.args.LeftPipetteFirstTip)

        try:
            right_available = \
                (len(self.right_tip_boxes)*96)-tip_box_layout.index(self.args.RightPipetteFirstTip.upper())
        except ValueError:
            msg += "Starting tip definition {} for Right Pipette is not valid\n".format(self.args.RightPipetteFirstTip)

        if msg:
            return msg

        if self.LeftPipette == "p300_single_gen2":
            if left_available < 0:
                left_available = 0
            if left_available < left_tips_used:
                msg += "Program requires {},  {} tips.  \n{} tips provided.\n\n"\
                    .format(left_tips_used, self.LeftPipette, left_available)

        if self.RightPipette == "p20_single_gen2":
            if right_available < 0:
                right_available = 0
            if right_available < right_tips_used:
                msg += "Program requires {},  {} tips.  \n{} tips provided"\
                    .format(int(right_tips_used), self.RightPipette, right_available)
        return msg

    def missing_parameters(self):
        msg = ""
        reagent_labware = ""
        if not self.args.ReagentSlot:
            msg += "--ReagentSlot is not defined.\n"
        if not self.args.PCR_Volume:
            msg += "--PCR_Volume is not defined.\n"
        if self.args.Template.strip() == "Illumina Dual Indexing":
            if not self.args.TotalReagentVolume:
                msg += "--TotalRegentVolume is not defined.\n"
            if not self.args.DNA_in_Reaction:
                msg += "--DNA_in_Reaction is not defined\n"
        if not self.args.WaterResVol:
            msg += "--WaterResVol is not defined\n"
        if self.args.UseTemperatureModule:
            if not self.args.Temperature:
                msg += "--Temperature is not defined.\n"
            if int(self.args.Temperature) < 5 or int(self.args.Temperature) > 99:
                msg += "--Temperature must be between 5 and 99.\n"
        if self.args.Temperature and not self.args.UseTemperatureModule:
            msg += "--UseTemperatureModule is not defined but a --Temperature is provided.\n"

        if self.args.ReagentSlot:
            try:
                reagent_labware = self.slot_dict[self.args.ReagentSlot]
            except KeyError:
                msg += "--ReagentSlot {} has no labware defined".format(self.args.ReagentSlot)

        return msg, reagent_labware

    def illumina_dual_indexing(self, template):

        if self.args.Version != "v2.0.1":
            return "{} template must be v2.0.1, you are using {}".format(template, self.args.Version)

        msg, reagent_labware = self.missing_parameters()

        if not self.args.PCR_ReagentWell:
            msg += "--PCR_ReagentWell is not defined"

        if not self.args.IndexPrimerSlot:
            msg += "--IndexPrimerSlot is not defined"

        try:
            self.slot_dict[self.args.IndexPrimerSlot]
        except KeyError:
            msg += "--IndexPrimerSlot {} has no labware defined".format(self.args.IndexPrimerSlot)

        if msg:
            return msg

        # Check for slot conflicts
        msg = self.slot_usage_error_check(reagent_labware, type_check="Reagent")
        if msg:
            return msg

        msg = self.slot_usage_error_check(self.slot_dict[self.args.IndexPrimerSlot], type_check="Index Primers")

        if msg:
            return msg

        self.max_template_vol = round(float(self.args.PCR_Volume) - float(self.args.MasterMixPerRxn), ndigits=1)

        for key in self.well_label_dict:
            label_list = self.well_label_dict[key]
            if key in reagent_labware:
                if self.args.WaterResWell.upper() not in label_list:
                    msg = "The water well definition is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

        # Process Sample data;
        source_test = {}
        index_dict = {}
        sample_dest_slot = self.args.PCR_PlateSlot

        if len(self.sample_dictionary) == 0:
            return "Sample information section error.  Possible missing sample slot."

        msg = ""
        for sample_key in self.sample_dictionary:
            sample_source_slot = self.sample_dictionary[sample_key][0]
            sample_source_well = self.sample_dictionary[sample_key][1]
            sample_index = self.sample_dictionary[sample_key][2]
            sample_name = self.sample_dictionary[sample_key][3]
            sample_dest_well = self.sample_dictionary[sample_key][5]

            if not sample_source_well:
                msg += "Sample Source Well is not defined for sample {}".format(sample_name)
            if not sample_index:
                msg += "Sample Index is not defined for sample {}".format(sample_name)
            if not sample_name:
                msg += "Sample Name is not defined for sample in Slot {}, Well {}"\
                    .format(sample_source_slot, sample_source_well)
            if not sample_dest_well:
                msg += "Destination Well is not defined for sample {}".format(sample_name)

            if sample_index in index_dict:
                msg += "Sample index {} used for samples {} and {}"\
                    .format(sample_index, index_dict[sample_index], sample_name)
                return msg
            else:
                index_dict[sample_index] = sample_name

            source_key = "{}+{}".format(sample_source_slot, sample_source_well)
            if source_key in source_test:
                msg += ("Sample {} and sample {} are both assigned Slot {}, Source Well {}"
                        .format(source_test[source_key], sample_name, sample_source_slot, sample_source_well))
                print("ERROR:  {}".format(msg))
                return msg
            else:
                source_test[source_key] = sample_name

            # Make sure the sample source and destination slots are not tip boxes.
            msg += self.slot_usage_error_check(self.slot_dict[sample_source_slot], type_check=sample_name)
            msg += self.slot_usage_error_check(self.slot_dict[sample_dest_slot], type_check="{} DESTINATION"
                                               .format(sample_name))
            if msg:
                return msg

        wells_used = len(self.sample_dictionary)
        water_required, left_tips_used, right_tips_used, msg = self.pcr_sample_processing(wells_used, indexing_rxn=True)

        # This is our warning of samples being too dilute.
        if msg:
            return msg

        # Check Water Volume
        if float(self.args.WaterResVol) < water_required:
            msg = "Program requires minimum of {} uL water.  You have {} uL."\
                .format(water_required, self.args.WaterResVol)
            return msg

        # Check PCR reagent volume
        pcr_mix_required = float(self.args.PCR_Volume)*0.5*wells_used

        if pcr_mix_required > float(self.args.TotalReagentVolume):
            msg = "Program requires {} uL of PCR mix.  You have {} uL"\
                .format(pcr_mix_required, self.args.TotalReagentVolume)
            return msg

        # Check if there are enough tips
        msg = self.available_tips(left_tips_used, right_tips_used)
        if msg:
            return msg

    def well_labels(self):
        """
        Create a dictionary of well labels for each loaded labware.
        :return:
        """

        def well_list(row_count, column_count):
            row_labels = \
                ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
                 "U", "V", "W", "X", "Y", "Z"]

            temp_list = []
            for r in range(row_count):
                for i in range(column_count):
                    temp_list.append("{}{}".format(row_labels[r], i + 1))

            return temp_list

        well_labels_dict = defaultdict(list)
        for labware in self.labware_slot_definitions:
            w384 = well_list(12, 32)
            w96 = well_list(8, 12)
            w24 = well_list(4, 6)
            w15 = well_list(3, 5)

            if "24" in labware:
                well_labels_dict[labware] = w24
            elif "384" in labware:
                well_labels_dict[labware] = w384
            elif "96" in labware or "8_well" in labware or "ddpcr_plate" in labware:
                well_labels_dict[labware] = w96
            elif "_15_tuberack" in labware:
                well_labels_dict[labware] = w15
            elif len(well_labels_dict) == 0:
                msg = "Well label definitions failed.  Incorrect labware passed.  Template file is bad"
                print("ERROR:  {}".format(msg))
                return msg

        return well_labels_dict

    def pipette_definition_error_check(self, error_state, pipette, pipette_str):
        if pipette not in self.pipette_info_dict:
            error_state = True
            # print("ERROR:  {} definition not correct".format(pipette_str))
        return error_state

    def pcr_sample_processing(self, used_wells, indexing_rxn=False):
        """
        Only used in dual indexing.
        :param used_wells:
        :param indexing_rxn:
        :return:
        """
        sample_parameters = self.sample_dictionary
        pcr_mix_required = float(self.args.PCR_Volume) * 0.5
        # Force the user to have 1 extra tip as a buffer.
        left_tips_used = 1
        right_tips_used = 1

        indexing_tips = 0
        if indexing_rxn:
            indexing_tips = used_wells*2

        if self.LeftPipette == "p20_single_gen2" and pcr_mix_required <= 20:
            left_tips_used = used_wells+indexing_tips
        elif self.LeftPipette == "p300_single_gen2" and pcr_mix_required > 20:
            left_tips_used = used_wells+indexing_tips

        if self.RightPipette == "p20_single_gen2" and pcr_mix_required <= 20:
            right_tips_used = used_wells+indexing_tips
        elif self.RightPipette == "p300_single_gen2" and pcr_mix_required > 20:
            right_tips_used = used_wells+indexing_tips

        template_required = float(self.args.DNA_in_Reaction)
        water_required = 0
        msg = ""
        for sample_key in sample_parameters:
            if indexing_rxn:
                sample_concentration = float(sample_parameters[sample_key][4])
            else:
                sample_concentration = float(sample_parameters[sample_key][3])

            sample_vol = round(template_required/sample_concentration, ndigits=1)

            # Check sample concentration.  At the first low concentration sample return a message.
            msg = self.sample_concentration_check(sample_vol, sample_concentration, sample_parameters[sample_key][2])
            if msg:
                return 0, 0, False, msg

            water_vol = (float(self.args.PCR_Volume)*0.5)-sample_vol
            if indexing_rxn:
                'Indexing reactions use 2 uL of each indexing primer'
                water_vol = water_vol - 4

            dilution_required = False

            if sample_vol <= 2.0 and not getattr(self.args, "DilutionPlateSlot"):
                msg += "Sample {} requires dilution but no --DilutionPlateSlot given.\n"\
                    .format(sample_parameters[sample_key][2])

            if dilution_required and not self.labware_slot_definitions[self.args.DilutionPlateSlot]:
                msg += "Slot {} requires Labware for dilutions".format(self.args.DilutionPlateSlot)

            if msg:
                return 0, 0, True, msg

            water_required += water_vol
            left_tips_used, right_tips_used = self.tip_counter(left_tips_used, right_tips_used, water_vol)
            left_tips_used, right_tips_used = self.tip_counter(left_tips_used, right_tips_used, sample_vol)

        return round(water_required, ndigits=1), left_tips_used, right_tips_used, msg

    def tip_counter(self, left_tips_used, right_tips_used, volume):
        if self.LeftPipette == "p20_single_gen2" and volume <= 20:
            left_tips_used += 1
        elif self.LeftPipette == "p300_single_gen2" and volume > 20:
            left_tips_used += 1

        if self.RightPipette == "p20_single_gen2" and volume <= 20:
            right_tips_used += 1
        elif self.RightPipette == "p300_single_gen2" and volume > 20:
            right_tips_used += 1

        return left_tips_used, right_tips_used

    def sample_concentration_check(self, template_in_rxn, sample_concentration, sample_name):
        """
        Check if sample concentration is sufficient.
        :param template_in_rxn:
        :param sample_concentration:
        :param sample_name:
        :return:
        """
        msg = ""
        if (template_in_rxn/sample_concentration) > self.max_template_vol:
            min_sample_conc = round(template_in_rxn / self.max_template_vol, ndigits=1)
            msg = "Sample '{}' at {} ng/uL is too dilute.\nMinimum sample concentration required is {} ng/uL for " \
                  "a max template volume of {} uL" \
                .format(sample_name, sample_concentration, min_sample_conc, self.max_template_vol)

        return msg

    def sample_processing(self):
        """
        Parse sample information
        :rtype: int
        """

        # Check if destination PCR plate and dilution labware are tip boxes
        msg = self.slot_usage_error_check(self.slot_dict[self.args.PCR_PlateSlot], type_check="PCR Plate")
        if msg:
            return "", "", "", "", "", msg

        sample_parameters = self.sample_dictionary

        plate_layout_by_column, layout_data = plate_layout(self.slot_dict[self.args.PCR_PlateSlot])
        sample_data_dict = defaultdict(list)
        target_well_dict = defaultdict(list)
        water_well_dict = defaultdict(float)
        used_wells = []
        dest_well_count = 0
        # template_in_rxn = float(self.args.DNA_in_Reaction)
        template_in_rxn = getattr(self.args, "DNA_in_Reaction", None)

        if len(sample_parameters) == 0:
            return "", "", "", "", "", "No samples defined in parameter template or sample slot is missing."

        for sample_key in sample_parameters:
            msg = ""
            sample_name = sample_parameters[sample_key][2]
            sample_slot = sample_parameters[sample_key][0]
            sample_well = sample_parameters[sample_key][1]
            targets = sample_parameters[sample_key][4].split(",")

            if self.args.Template.strip() != "Illumina_Dual_Indexing":
                try:
                    replicates = int(sample_parameters[sample_key][5])
                except ValueError:
                    msg += "Replica count not defined for sample {}\n".format(sample_name)

            try:
                sample_concentration = float(sample_parameters[sample_key][3])
            except ValueError:
                msg += "Concentration not defined for sample {}\n".format(sample_name)

            # Generic PCR allows different amounts of template for each sample.
            if template_in_rxn:
                template_in_rxn = float(template_in_rxn)
            else:
                try:
                    template_in_rxn = float(sample_parameters[sample_key][6])
                except ValueError:
                    msg += "Amount of template in reaction not defined for sample {}\n".format(sample_name)

            if not sample_name:
                msg += "No Sample Name defined for sample in Slot {}, Well {}\n".format(sample_slot, sample_well)
            if not sample_slot:
                msg += "Sample Slot not defined for sample {}\n".format(sample_name)
            if not sample_well:
                msg += "Sample Well not defined for sample {}\n".format(sample_name)

            if all('' == s or s.isspace() for s in targets):
                msg += "Targets not defined for sample {}\n".format(sample_name)

            if msg:
                return "", "", "", "", "", msg

            msg = \
                self.sample_concentration_check(template_in_rxn, sample_concentration, sample_name)
            if msg:
                return "", "", "", "", "", msg

            sample_vol, diluent_vol, diluted_sample_vol, reaction_water_vol, max_template_vol, msg = \
                calculate_volumes(self.args, sample_concentration, template_in_rxn, sample_name,
                                  self.slot_dict)

            if msg:
                return "", "", "", "", "", msg

            if self.args.Template.strip() == "Illumina_Dual_Indexing":
                replicates = 1

            sample_wells = []
            for target in targets:
                for i in range(replicates):
                    well = plate_layout_by_column[dest_well_count]
                    water_well_dict[well] = reaction_water_vol
                    target_well_dict[target].append(well)
                    sample_wells.append(well)
                    used_wells.append(well)
                    dest_well_count += 1

            sample_data_dict[sample_key] = [sample_vol, diluent_vol, diluted_sample_vol, sample_wells]
        if self.args.Template.strip() != "Illumina_Dual_Indexing":
            # Define our no template control wells for the targets.
            for i in range(len(target_well_dict)):
                well = plate_layout_by_column[dest_well_count]
                used_wells.append(well)
                water_well_dict[well] = self.max_template_vol
                dest_well_count += 1

        return sample_data_dict, water_well_dict, target_well_dict, used_wells, layout_data, msg

    def empty_well_vol(self, plate_data, used_well_count, p20_tip_count, p300_tip_count, total_water):
        """
        This will determine the amount of water and number of tips required to fill the remaining empty wells in a
        column.

        :param plate_data:
        :param used_well_count:
        :param p20_tip_count:
        :param p300_tip_count:
        :param total_water:
        :return:
        """

        plate_template = plate_data[0]
        last_used_well = plate_template[used_well_count-1]
        row = last_used_well[0]
        column = int(last_used_well.split(row)[1])
        wells_remaining = 12 - column
        total_water += wells_remaining*float(self.args.PCR_Volume)
        p20_tip_count, p300_tip_count = self.tip_counter(p20_tip_count, p300_tip_count, float(self.args.PCR_Volume))

        return total_water, p20_tip_count, p300_tip_count

    def calculate_volumes(self, sample_concentration):
        """
        Calculates volumes for dilution and distribution of sample.
        Returns a list of tuples consisting of
        (uL of sample to dilute, uL of water for dilution), (uL of diluted sample in reaction, uL of water in reaction)
        @param sample_concentration:
        @return:
        """

        template_in_reaction = float(self.args.DNA_in_Reaction)
        # Target Concentration is used to keep volumes > 1 uL
        target_concentration = template_in_reaction / 2

        """
        # There is the potential to need the max template volume for the lower dilutions.  This defines those.
        # Not needed.  Simply make extra volume based on number of replicates.
        dilution_template = [(4, 4), (2, 6), (2, 10), (1, 7), (1, 9), (1, 11)]
        if args.PCR_MixConcentration == "4x":
            dilution_template = [(7, 7), (4, 12), (3, 15), (2, 14), (2, 18), (2, 22)]
        """
        min_dna_in_reaction = template_in_reaction / self.max_template_vol

        # If template concentration per uL is less than desired template in reaction then no dilution is necessary.
        if sample_concentration <= target_concentration:
            sample_vol = template_in_reaction / sample_concentration
            return sample_vol, 0, round(self.max_template_vol - sample_vol, ndigits=1), self.max_template_vol

        # This will test a series of dilutions up to a 1:200.
        for i in range(50):
            dilution = (i + 1) * 2
            diluted_dna_conc = sample_concentration / dilution

            if target_concentration >= diluted_dna_conc >= min_dna_in_reaction:
                dilution_data = (1, dilution - 1)
                diluted_sample_vol = round(template_in_reaction / diluted_dna_conc, ndigits=1)
                reaction_water_vol = self.max_template_vol - diluted_sample_vol

                return dilution_data[0], dilution_data[1], diluted_sample_vol, reaction_water_vol
