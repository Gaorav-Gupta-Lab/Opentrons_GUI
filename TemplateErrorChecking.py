
"""
Dennis A Simpson
University of North Carolina at Chapel Hill
450 West Drive
Chapel Hill, NC  27599

@Copyright 2022
"""

import sys
from distutils import log
from collections import defaultdict
from types import SimpleNamespace
import csv
# import Tool_Box
from Utilities import parse_sample_template, calculate_volumes, plate_layout

__version__ = "1.0.1"


class TemplateErrorChecking:
    def __init__(self, input_file):
        self.stdout = sys.stdout
        self.sample_dictionary, self.args = parse_sample_template(input_file)
        self.pipette_info_dict = {"p10_multi": "opentrons_96_tiprack_10ul",
                                  "p10_single": "opentrons_96_tiprack_10ul",
                                  "p20_single_gen2": ["opentrons_96_tiprack_20ul", "opentrons_96_filtertiprack_20ul"],
                                  "p300_single_gen2": ["opentrons_96_tiprack_300ul", "opentrons_96_filtertiprack_300ul"]
                                  }
        self.slot_dict = None
        self.left_tip_boxes = []
        self.right_tip_boxes = []
        self.max_template_vol = None
        self.well_label_dict = self.well_labels()

    def parameter_checks(self):
        """
        Make sure various parameters that are common to all setups exist in the parameter template.
        :return:
        """

        msg = ""
        if not self.args.PCR_Volume:
            msg += "--PCR_Volume parameter is missing from template.\n"
        if not self.args.ReagentVolume:
            msg += "--ReagentVolume parameter is missing from template.\n"
        if not self.args.WaterResVol:
            msg += "--WaterResVol parameter is missing from template.\n"
        if not self.args.WaterResWell:
            msg += "--WaterResWell parameter is not defined in template.\n"
        if not self.args.ReagentSlot:
            msg += "--ReagentSlot parameter is not defined in template.\n"
        if not self.args.PCR_PlateSlot:
            msg += "--PCR_PlateSlot parameter is not defined in template.\n"

        return msg

    @staticmethod
    def parse_sample_file(input_file):
        """
        Parse TSV file
        :param input_file:
        :return:
        """
        line_num = 0
        options_dictionary = defaultdict(str)
        sample_dictionary = defaultdict(list)
        index_file = list(csv.reader(open(input_file), delimiter='\t'))

        for line in index_file:
            # Get the program linked to the template file.  Data should always be the first cell of line one.
            if line_num == 0:
                options_dictionary["Program"] = line[0]

            line_num += 1
            col_count = len(line)
            tmp_line = []
            sample_key = ""
            if col_count > 0 and "#" not in line[0] and len(line[0].split("#")[0]) > 0:
                # Skip any lines that are blank or comments.

                for i in range(7):
                    try:
                        line[i] = line[i].split("#")[0]  # Strip out end of line comments and white space.
                    except IndexError:
                        continue

                    if i == 0 and "--" in line[0]:
                        key = line[0].strip('--')
                        key_value = line[1]
                        if "Target_" in key or "PositiveControl_" in key:
                            key_value = (line[1], line[2], line[3])
                        options_dictionary[key] = key_value
                    elif "--" not in line[0] and int(line[0]) < 12:
                        sample_key = line[0], line[1]
                        tmp_line.append(line[i])
                if sample_key:
                    sample_dictionary[sample_key] = tmp_line

        return sample_dictionary, SimpleNamespace(**options_dictionary)

    def slot_error_check(self):
        """
        Make sure the slots contain valid labware definitions and check for inappropriate labware such as a pipette
        tip box in the defined reagent slot.
        :return:
        """
        slot_error = ""
        slot_list = \
            ["Slot1", "Slot2", "Slot3", "Slot4", "Slot5", "Slot6", "Slot7", "Slot8", "Slot9", "Slot10", "Slot11"]

        slot_dict = {}
        print("Checking Labware Definitions in Slots")

        for i in range(len(slot_list)):
            labware = getattr(self.args, "{}".format(slot_list[i]))

            if labware and labware not in self.labware_slot_definitions:
                msg = "ERROR: Slot {} labware definition not in dictionary.\nCheck spelling.".format(slot_list[i])
                slot_error = msg
            elif labware:
                slot_dict[str(i + 1)] = labware

        if slot_error:
            print("NOTICE: There are errors in the labware definitions.  Correct these and run again\n")
        else:
            print("\tLabware definitions in slots passed")

        self.slot_dict = slot_dict

        return slot_error

    def pipette_error_check(self):
        """
        This will check if the pipette definition given in the template file is proper.  It will not check if these
        match what is actually installed on the robot.
        :return:
        """
        msg = ""
        pipette_error = False
        log.info("Checking Pipette Definitions")
        if self.args.LeftPipette:
            pipette_error = self.pipette_definition_error_check(pipette_error, self.args.LeftPipette, "Left Pipette")
        if self.args.RightPipette:
            pipette_error = self.pipette_definition_error_check(pipette_error, self.args.RightPipette, "Right Pipette")
        if pipette_error:
            msg = "There is an error in the one of the pipette definitions"
            print("ERROR: {}".format(msg))
        else:
            print("\tPipette definitions passed.")

        return msg

    def tip_box_error_check(self):
        print("Checking Pipette Tip Box Definitions")
        msg = ""
        for slot in self.slot_dict:
            labware = self.slot_dict[slot]
            lft_pipette_labware = self.pipette_info_dict[self.args.LeftPipette]
            rt_pipette_labware = self.pipette_info_dict[self.args.RightPipette]
            if labware in lft_pipette_labware:
                self.left_tip_boxes.append(slot)
            elif labware in rt_pipette_labware:
                self.right_tip_boxes.append(slot)

        if len(self.left_tip_boxes) == 0 == len(self.right_tip_boxes):
            print("ERROR:  No pipette tip boxes defined.")
            msg = "ERROR:  No pipette tip boxes defined."

        else:
            print("\tPipette tip box definitions passed")

        return msg

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
                        msg += "{} Well definition is the same as the --WaterResWell".format(target[i])
                    if not target[1]:
                        msg += "{} Target Name definition is missing".format(target[i])
                    if not target[2]:
                        msg += "{} Volume definition is missing".format(target[i])

        if no_target_count == 10:
            msg = "No targets defined"

        return target_count, msg

    def pcr_check(self, template):
        """
        Test ddPCR and Generic PCR templates.
        type template: object
        :rtype: object
        """
        if template == " Generic PCR" and self.args.Version != "v1.0.0":
            return "{} template must be v1.0.0, you are using {}".format(template, self.args.Version)
        elif template == " ddPCR" and self.args.Version != "v1.0.0":
            return "{} template must be v1.0.0, you are using {}".format(template, self.args.Version)

        msg, reagent_labware = self.missing_parameters()

        if msg:
            return msg

        self.max_template_vol = round(float(self.args.PCR_Volume) - float(self.args.ReagentVolume), 1)
        msg = self.slot_usage_error_check(reagent_labware, type_check="Reagent")

        if msg:
            return msg

        target_count, msg = self.pcr_targets()

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
            water_vol = water_well_dict[well]
            if water_vol <= 20:
                p20_tips_used += 1
            else:
                p300_tips_used += 1
            water_aspirated += water_vol

        target_well_count = 0
        for target in target_well_dict:
            # Force user to include extra reagent in tube to account for pipetting errors
            reagent_used = float(self.args.ReagentVolume) * 1.5

            # Get information about the master mix
            target_info = getattr(self.args, "Target_{}".format(target))
            reagent_well_vol = float(target_info[2])

            # How much master mix per reaction?
            reagent_aspirated = float(self.args.ReagentVolume)

            target_well_list = target_well_dict[target]

            # Count the number of tips required
            for well in target_well_list:
                reagent_used += reagent_aspirated
                if reagent_aspirated <= 20:
                    p20_tips_used += 1
                else:
                    p300_tips_used += 1

            # Add a reagent tips for the no template control
            if float(self.args.PCR_Volume)-reagent_aspirated <= 20:
                p20_tips_used += 2
            else:
                p300_tips_used += 2

            target_well_count += len(target_well_list)
            if reagent_used >= reagent_well_vol:
                reagent_name = target_info[1]
                msg = "Program requires minimum of {} uL of Target {}.  You have {} uL."\
                      .format(reagent_used, reagent_name, reagent_well_vol)
                return msg

        water_aspirated, p20_tips_used, p300_tips_used = \
            self.dispense_samples(sample_data_dict, water_aspirated, p20_tips_used, p300_tips_used)

        if target_well_count == 0:
            return "Number of wells containing targets is 0.  Check TSV file for errors in sample table."

        water_aspirated, p20_tips_used, p300_tips_used = \
            self.empty_well_vol(plate_layout(self.slot_dict[self.args.PCR_PlateSlot]), target_well_count, p20_tips_used,
                                p300_tips_used, water_aspirated)

        # Check Water Volume
        if int(self.args.WaterResVol) <= water_aspirated:
            msg = "Program requires minimum of {} uL water.  You have {} uL."\
                .format(water_aspirated, self.args.WaterResVol)
            return msg

        # Check if there are enough tips
        msg = self.available_tips(p20_tips_used, p300_tips_used)
        if msg:
            return msg

    def available_tips(self, left_tips_used, right_tips_used):
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

        if self.args.LeftPipette == "p20_single_gen2":
            if left_available < 0:
                left_available = 0
            if left_available < left_tips_used:
                msg += "Program requires {}, {} tips.  {} tips provided.\n"\
                    .format(left_tips_used, self.args.LeftPipette, left_available)

        if self.args.RightPipette == "p300_single_gen2":
            if right_available < 0:
                right_available = 0
            if right_available < right_tips_used:
                msg += "Program requires {}, {} tips.  {} tips provided"\
                    .format(int(right_tips_used), self.args.RightPipette, right_available)
        return msg

    def missing_parameters(self):
        msg = ""
        reagent_labware = ""
        if not self.args.ReagentSlot:
            msg += "--ReagentSlot is not defined.\n"
        if not self.args.PCR_Volume:
            msg += "--PCR_Volume is not defined.\n"
        if not self.args.ReagentVolume:
            msg += "--RegentVolume is not defined.\n"
        if not self.args.WaterResVol:
            msg += "--WaterResVol is not defined"
        if self.args.Template == " Illumina Dual Indexing" and not self.args.DNA_in_Reaction:
            msg += "--DNA_in_Reaction is not defined"

        if self.args.ReagentSlot:
            try:
                reagent_labware = self.slot_dict[self.args.ReagentSlot]
            except KeyError:
                msg += "--ReagentSlot {} has no labware defined".format(self.args.ReagentSlot)

        return msg, reagent_labware

    def illumina_dual_indexing(self, template):

        if self.args.Version != "v1.0.0":
            return "{} template must be v1.0.0, you are using {}".format(template, self.args.Version)

        msg, reagent_labware = self.missing_parameters()

        if not self.args.PCR_ReagentWell:
            msg += "--PCR_ReagentWell is not defined"

        if not self.args.IndexPrimerSlot:
            msg += "--IndexPrimerSlot is not defined"

        try:
            self.slot_dict[self.args.IndexPrimerSlot]
        except KeyError:
            msg += "--IndexPrimerSlot {} has no labware defined".format(self.args.IndexPrimerSlot)

        try:
            self.slot_dict[self.args.PCR_PlateSlot]
        except KeyError:
            msg += "--PCR_PlateSlot {} has no labware defined".format(self.args.PCR_PlateSlot)

        if msg:
            return msg

        # Check for slot conflicts
        msg = self.slot_usage_error_check(reagent_labware, type_check="Reagent")
        if msg:
            return msg

        msg = self.slot_usage_error_check(self.slot_dict[self.args.IndexPrimerSlot], type_check="Index Primers")

        if msg:
            return msg

        self.max_template_vol = round(float(self.args.PCR_Volume) - float(self.args.ReagentVolume), 1)

        for key in self.well_label_dict:
            label_list = self.well_label_dict[key]
            if key in reagent_labware:
                if self.args.WaterResWell.upper() not in label_list:
                    msg = "The water well definition is not possible for {}".format(reagent_labware)
                    print("ERROR: {}".format(msg))
                    return msg

        # Process Sample data;
        source_test = []
        dest_test = []
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
                msg += "Sample Source Well is not defined for sample {}".format(self.sample_dictionary[sample_key][3])
            if not sample_index:
                msg += "Sample Index is not defined for sample {}".format(self.sample_dictionary[sample_key][3])
            if not sample_name:
                msg += "Sample Name is not defined for sample in Slot {}, Well {}"\
                    .format(sample_source_slot, sample_source_well)
            if not sample_dest_well:
                msg += "Destination Well is not defined for sample {}".format(self.sample_dictionary[sample_key][3])

            source_test.append("{}+{}".format(sample_source_slot, sample_source_well))
            # Make sure the sample source and destination slots are not tip boxes.
            msg += self.slot_usage_error_check(self.slot_dict[sample_source_slot], type_check=sample_name)
            if msg:
                return msg

            msg = self.slot_usage_error_check(self.slot_dict[sample_dest_slot], type_check="{} DESTINATION"
                                              .format(sample_name))
            if msg:
                return msg

            if sample_index in index_dict:
                msg = "Sample index {} used for samples {} and {}"\
                    .format(sample_index, index_dict[sample_index], sample_name)
                return msg
            else:
                index_dict[sample_index] = sample_name

        dest_test.append("{}+{}".format(sample_dest_slot, sample_dest_well))
        for source in source_test:
            if source in dest_test:
                msg = "More than one sample share the same source and/or destinations"
                print("ERROR:  {}".format(msg))
                return msg

        wells_used = len(dest_test)
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

        if pcr_mix_required > float(self.args.ReagentVolume):
            msg = "Program requires {} uL of PCR mix.  You have {} uL"\
                .format(pcr_mix_required, self.args.ReagentVolume)
            return msg

        # Check if there are enough tips
        msg = self.available_tips(left_tips_used, right_tips_used)
        if msg:
            return msg

    @property
    def labware_slot_definitions(self):
        """
        Labware that we have on-hand.
        :return:
        """
        labware_list = [
            "vwrmicrocentrifugetube1.5ml_24_tuberack_1500ul", "stacked_96_well", "8_well_strip_tubes_200ul",
            "opentrons_96_tiprack_10ul", "opentrons_96_tiprack_20ul", "opentrons_96_tiprack_300ul",
            "vwrscrewcapcentrifugetube5ml_15_tuberack_5000ul", "screwcap_24_tuberack_500ul",
            "opentrons_24_tuberack_generic_2ml_screwcap", "opentrons_96_filtertiprack_20ul",
            "opentrons_96_filtertiprack_20ul"]

        return labware_list

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
            w96 = well_list(8, 12)
            w24 = well_list(4, 6)
            w15 = well_list(3, 5)

            if "24" in labware:
                well_labels_dict[labware] = w24
            elif "96" in labware or "8_well" in labware:
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
            print("ERROR:  {} definition not correct".format(pipette_str))
        return error_state

    def pcr_sample_processing(self, used_wells, indexing_rxn=False):
        sample_parameters = self.sample_dictionary
        pcr_mix_required = float(self.args.PCR_Volume) * 0.5
        indexing_tips = 0
        if indexing_rxn:
            indexing_tips = used_wells*2

        # Force the user to have 4 extra tips as a buffer.
        left_tips_used = 4
        right_tips_used = 4
        if self.args.LeftPipette == "p20_single_gen2" and pcr_mix_required <= 20:
            left_tips_used = used_wells+indexing_tips
        elif self.args.LeftPipette == "p300_single_gen2" and pcr_mix_required > 20:
            left_tips_used = used_wells

        if self.args.RightPipette == "p20_single_gen2" and pcr_mix_required <= 20:
            right_tips_used = used_wells+indexing_tips
        elif self.args.RightPipette == "p300_single_gen2" and pcr_mix_required > 20:
            right_tips_used = used_wells

        template_required = float(self.args.DNA_in_Reaction)
        water_required = 0
        msg = ""
        for sample_key in sample_parameters:
            if indexing_rxn:
                sample_concentration = float(sample_parameters[sample_key][4])
            else:
                sample_concentration = float(sample_parameters[sample_key][3])
            sample_vol = round(template_required/sample_concentration, 2)
            water_vol = (float(self.args.PCR_Volume)*0.5)-sample_vol

            if sample_vol <= 1.1 and not getattr(self.args, "DilutionPlateSlot"):
                msg = "Sample {} requires dilution but no --DilutionPlateSlot given."\
                    .format(sample_parameters[sample_key][2])

                return 0, 0, True, msg

            # Check sample concentration.  At the first low concentration sample return a message.
            msg = self.sample_concentration_check(sample_vol, sample_concentration, sample_parameters[sample_key][2])
            if msg:
                return 0, 0, False, msg

            water_required += water_vol
            left_tips_used, right_tips_used = self.tip_counter(left_tips_used, right_tips_used, water_vol)
            left_tips_used, right_tips_used = self.tip_counter(left_tips_used, right_tips_used, sample_vol)

        return round(water_required, 1), left_tips_used, int(right_tips_used), msg

    def tip_counter(self, left_tips_used, right_tips_used, volume):
        if self.args.LeftPipette == "p20_single_gen2" and volume <= 20:
            left_tips_used += 1
        elif self.args.LeftPipette == "p300_single_gen2" and volume > 20:
            left_tips_used += 1

        if self.args.RightPipette == "p20_single_gen2" and volume <= 20:
            right_tips_used += 1
        elif self.args.RightPipette == "p300_single_gen2" and volume > 20:
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
            min_sample_conc = round(template_in_rxn / self.max_template_vol, 2)
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

        # There is a single no template control for every target that uses max volume.
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

            msg = self.sample_concentration_check(template_in_rxn, sample_concentration, sample_name)
            if msg:
                return "", "", "", "", "", msg

            sample_vol, diluent_vol, diluted_sample_vol, reaction_water_vol, max_template_vol, msg = \
                calculate_volumes(self.args, sample_concentration, template_in_rxn, sample_name)

            if msg:
                return "", "", "", "", "", msg

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

        # Define our positive control wells for the targets.
        # FixMe: Confirm this block actually does something that is needed
        for target in target_well_dict:
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
            return sample_vol, 0, round(self.max_template_vol - sample_vol, 2), self.max_template_vol

        # This will test a series of dilutions up to a 1:200.
        for i in range(50):
            dilution = (i + 1) * 2
            diluted_dna_conc = sample_concentration / dilution

            if target_concentration >= diluted_dna_conc >= min_dna_in_reaction:
                dilution_data = (1, dilution - 1)
                diluted_sample_vol = round(template_in_reaction / diluted_dna_conc, 2)
                reaction_water_vol = self.max_template_vol - diluted_sample_vol

                return dilution_data[0], dilution_data[1], diluted_sample_vol, reaction_water_vol
